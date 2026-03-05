# Copyright (c) Simon Niederberger.
# Distributed under the terms of the Modified BSD License.

import matplotlib.dates as mdates
import matplotlib.scale as mscale
import matplotlib.transforms as mtransforms
import numpy as np
import pandas as pd

from busdayaxis._locator import BusdayLocator

EPOCH = np.datetime64("1970-01-01", "D")

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
WEEKDAYS_MAP = {name: i for i, name in enumerate(WEEKDAYS)}

#####################################################################
# Helper functions
#####################################################################


def _validate_hours(start, end, label="hours"):
    if not (0 <= start <= end <= 24):
        raise ValueError(f"{label} must satisfy 0 <= start <= end <= 24")


def _normalize_bushours(bushours):
    """Normalize bushours to a dict keyed by weekday (0=Mon, 6=Sun).

    Parameters
    ----------
    bushours : tuple, list, or dict
        - tuple (start, end): same hours for all weekdays
        - list of 7 tuples: hours for each weekday (Mon-Sun)
        - dict: weekday (0-6 or "Mon"–"Sun") -> (start, end)

    Returns
    -------
    dict
        weekday (0-6) -> (start_hour, end_hour)
    """
    if isinstance(bushours, dict):
        int_dict = {}

        for k, v in bushours.items():
            if isinstance(k, str) and k in WEEKDAYS_MAP:
                weekday = WEEKDAYS_MAP[k]
            elif isinstance(k, int) and 0 <= k <= 6:
                weekday = k
            else:
                raise ValueError(f"Got {k!r}; expected int 0-6 or name in {WEEKDAYS}")
            _validate_hours(*v, f"bushours for {WEEKDAYS[weekday]}")
            int_dict[weekday] = v
        return {i: int_dict.get(i, (0, 24)) for i in range(7)}

    if isinstance(bushours, (list, tuple)):
        if len(bushours) == 2 and all(isinstance(x, (int, float)) for x in bushours):
            _validate_hours(*bushours)
            return {i: bushours for i in range(7)}
        if len(bushours) == 7:
            for i, _bushours in enumerate(bushours):
                _validate_hours(*_bushours, f"bushours for {WEEKDAYS[i]}")
            return {i: bushours[i] for i in range(7)}

    raise ValueError(
        "bushours must be:\n"
        "  - tuple (start, end): same hours for all days\n"
        "  - list of 7 (start, end): hours for each weekday (Mon-Sun)\n"
        "  - dict {weekday: (start, end)}: per-weekday hours (keys: 0-6 or 'Mon'–'Sun')"
    )


def _datetime_to_busday_float(values, bushours_dict, **busday_kwargs) -> np.ndarray:
    """Convert datetime-like values to business-day floats.

    Mapping:
        business_day_index + intraday_fraction

    Intraday fraction is defined only inside business hours. Times outside
    that interval are clipped to the boundaries so that nights collapse
    to the endpoints of the business session.
    """
    values = pd.DatetimeIndex(pd.to_datetime(values))

    day = values.floor("D")
    intraday_fraction = (values - day).total_seconds() / 86400.0

    weekday = np.asarray(values.weekday)
    _starts = np.array([bushours_dict[i][0] for i in range(7)]) / 24
    _ends = np.array([bushours_dict[i][1] for i in range(7)]) / 24
    bushour_starts = _starts[weekday]
    bushour_ends = _ends[weekday]

    clipped = np.clip(intraday_fraction, bushour_starts, bushour_ends)

    duration = bushour_ends - bushour_starts
    normalized = np.where(duration > 0, (clipped - bushour_starts) / duration, 0.0)

    days_d64 = day.values.astype("datetime64[D]")
    rolled = np.busday_offset(days_d64, 0, roll="forward", **busday_kwargs)
    business_days = np.busday_count(EPOCH, rolled, **busday_kwargs)
    is_busday = np.is_busday(days_d64, **busday_kwargs)
    intraday = np.where(is_busday, normalized, 0.0)

    busday_float = (business_days + intraday).astype(float)
    return busday_float


def _busday_float_to_datetime(values, bushours_dict, **busday_kwargs):
    """Convert business-day floats back to datetime values.

    Note that the transform is not perfectly invertible because
    timestamps outside business hours are clipped during the forward
    transformation.
    """
    values = np.asarray(values, dtype=float)
    original_shape = values.shape
    values_flat = values.ravel()

    day_int = np.floor(values_flat).astype(int)

    date = np.busday_offset(
        EPOCH,
        day_int,
        roll="forward",
        **busday_kwargs,
    ).astype("datetime64[s]")

    intraday_fraction = values_flat - day_int

    weekday = np.asarray(pd.DatetimeIndex(date).weekday)
    _starts = np.array([bushours_dict[i][0] for i in range(7)]) / 24
    _ends = np.array([bushours_dict[i][1] for i in range(7)]) / 24
    bushour_starts = _starts[weekday]
    bushour_ends = _ends[weekday]

    duration = bushour_ends - bushour_starts

    scaled = np.where(
        duration > 0,
        intraday_fraction * duration + bushour_starts,
        bushour_starts,
    )

    intraday_seconds = (scaled * 86400.0).astype("int64").astype("timedelta64[s]")

    datetimes = (date + intraday_seconds).reshape(original_shape)
    return datetimes


#####################################################################
# Classes
#####################################################################


class _BusdayTransformBase(mtransforms.Transform):
    """Shared base for forward and inverse business-day transforms."""

    input_dims = 1
    output_dims = 1
    is_separable = True

    def __init__(self, bushours_dict, **busday_kwargs):
        self._bushours_dict = bushours_dict
        self._busday_kwargs = busday_kwargs
        super().__init__()


class BusdayTransform(_BusdayTransformBase):
    """Forward transform: matplotlib date numbers -> business-day floats.

    Maps each matplotlib date number (float, days since epoch) to a
    business-day float: integer part = business-day index, fractional
    part = normalised position within the active session.
    """

    def transform_non_affine(self, x):
        x = np.asarray(x)
        result = _datetime_to_busday_float(
            mdates.num2date(x.ravel()), self._bushours_dict, **self._busday_kwargs
        )
        return result.reshape(x.shape)

    def inverted(self):
        return InvertedBusdayTransform(self._bushours_dict, **self._busday_kwargs)


class InvertedBusdayTransform(_BusdayTransformBase):
    """Inverse transform: business-day floats -> matplotlib date numbers.

    Not perfectly invertible: timestamps outside business hours were
    clipped to session boundaries during the forward transform.
    """

    def transform_non_affine(self, x):
        x = np.asarray(x, dtype=float)
        dates = _busday_float_to_datetime(
            x.ravel(), self._bushours_dict, **self._busday_kwargs
        )
        return mdates.date2num(dates).reshape(x.shape)

    def inverted(self):
        return BusdayTransform(self._bushours_dict, **self._busday_kwargs)


class BusdayScale(mscale.ScaleBase):
    name = "busday"

    def __init__(self, axis, bushours=(0, 24), **busday_kwargs):
        self._bushours_dict = _normalize_bushours(bushours)
        self._busday_kwargs = busday_kwargs.copy()
        super().__init__(axis)

    def get_transform(self):
        return BusdayTransform(self._bushours_dict, **self._busday_kwargs)

    def set_default_locators_and_formatters(self, axis):
        axis._busday_kwargs = self._busday_kwargs.copy()
        axis._bushours = self._bushours_dict.copy()

        majloc = BusdayLocator(base_locator=mdates.AutoDateLocator())
        majloc.set_axis(axis)

        majfmt = mdates.AutoDateFormatter(majloc.base_locator)

        axis.set_major_locator(majloc)
        axis.set_major_formatter(majfmt)

    def limit_range_for_scale(self, vmin, vmax, minpos):
        return vmin, vmax


def register_scale():
    mscale.register_scale(BusdayScale)
