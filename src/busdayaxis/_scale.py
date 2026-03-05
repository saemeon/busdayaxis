# Copyright (c) Simon Niederberger.
# Distributed under the terms of the Modified BSD License.

import matplotlib.dates as mdates
import matplotlib.scale as mscale
import matplotlib.transforms as mtransforms
import numpy as np

from busdayaxis._locator import BusdayLocator

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
WEEKDAYS_MAP = {name: i for i, name in enumerate(WEEKDAYS)}

#####################################################################
# Helper functions
#####################################################################


def _validate_hours(start, end, label="hours"):
    if not (0 <= start <= end <= 24):
        raise ValueError(f"{label} must satisfy 0 <= start <= end <= 24")


def _normalize_bushours(bushours):
    """Return a dict ``{0..6: (start, end)}`` from any supported bushours form."""
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
        # Unspecified weekdays default to full day; weekends default to closed
        return {i: int_dict.get(i, (0, 0) if i >= 5 else (0, 24)) for i in range(7)}

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


def _bushours_bounds(bushours_dict):
    """Return (starts, ends) as numpy arrays of day-fractions (0–1) for all 7 weekdays."""
    starts = np.array([bushours_dict[i][0] for i in range(7)]) / 24
    ends = np.array([bushours_dict[i][1] for i in range(7)]) / 24
    return starts, ends


def _weekday_from_days(days_d64: np.ndarray) -> np.ndarray:
    """
    Compute weekday as 0=Mon, ..., 6=Sun for datetime64[D] arrays.

    1970-01-01 was a Thursday, which corresponds to weekday=3 in the
    Mon=0 convention.
    """
    return ((days_d64.view("int64") + 3) % 7).astype(int)


def _build_weighted_calendar(weights, **busday_kwargs):
    """Construct a lookup table mapping calendar days to cumulative
    weighted business-day coordinates."""

    days = np.arange(
        np.datetime64("1970-01-01", "D"),
        np.datetime64("2100-01-01", "D"),
        dtype="datetime64[D]",
    )

    weekday = _weekday_from_days(days)
    is_busday = np.is_busday(days, **busday_kwargs)

    day_weights = np.where(is_busday, weights[weekday], 0.0)
    cumulative = np.concatenate(([0.0], np.cumsum(day_weights)))

    return days, cumulative


def _datetime_to_busday_float(
    values, bushours_dict, calendar_days, cumulative, weights, **busday_kwargs
):
    """Convert datetime-like values to business-day floats.

    Mapping:
        business_day_weighted_index + intraday_fraction

    The first part corresponds to the cumulative weighted business-day index
    obtained from a precomputed calendar table. Days with shorter business
    hours therefore occupy a shorter span on the axis.

    The second part is the intraday fraction, which is defined only inside
    business hours. Times outside that interval are clipped to the boundaries
    so that nights collapse to the endpoints of the business session.
    """
    values = np.asarray(values, dtype="datetime64[ns]")

    day = values.astype("datetime64[D]")
    intraday_s = (
        (values - day.astype("datetime64[ns]"))
        .astype("timedelta64[s]")
        .astype(np.int64)
    )
    intraday_fraction = intraday_s / 86400.0

    weekday = _weekday_from_days(day)

    _starts, _ends = _bushours_bounds(bushours_dict)
    bushour_starts = _starts[weekday]
    bushour_ends = _ends[weekday]

    clipped = np.clip(intraday_fraction, bushour_starts, bushour_ends)

    duration = bushour_ends - bushour_starts
    normalized = np.where(duration > 0, (clipped - bushour_starts) / duration, 0.0)

    idx = (day - calendar_days[0]).astype(int)

    business_days = cumulative[idx]
    is_busday = np.is_busday(day, **busday_kwargs)
    intraday = np.where(is_busday, normalized * weights[weekday], 0.0)
    busday_float = (business_days + intraday).astype(float)
    return busday_float


def _busday_float_to_datetime(
    values, bushours_dict, calendar_days, cumulative, weights
):
    """Convert business-day floats back to datetime values.

    Note that the transform is not perfectly invertible because
    timestamps outside business hours are clipped during the forward
    transformation.
    """
    values = np.asarray(values, dtype=float)

    original_shape = values.shape
    values_flat = values.ravel()

    _starts, _ends = _bushours_bounds(bushours_dict)
    durations = _ends - _starts

    idx = np.searchsorted(cumulative, values_flat, side="right") - 1

    date_d = calendar_days[idx]
    weekday = _weekday_from_days(date_d)

    bushour_starts = _starts[weekday]
    bushour_durations = durations[weekday]

    base = cumulative[idx]

    intraday_fraction = np.divide(
        values_flat - base,
        weights[weekday],
        out=np.zeros_like(values_flat),
        where=weights[weekday] > 0,
    )

    scaled = bushour_starts + intraday_fraction * bushour_durations

    intraday_seconds = (scaled * 86400.0).astype("int64").astype("timedelta64[s]")

    datetimes = (date_d.astype("datetime64[s]") + intraday_seconds).reshape(
        original_shape
    )

    return datetimes


#####################################################################
# Classes
#####################################################################


class _BusdayTransformBase(mtransforms.Transform):
    """Shared base for forward and inverse business-day transforms."""

    input_dims = 1
    output_dims = 1
    is_separable = True

    def __init__(
        self, bushours_dict, calendar_days, cumulative, weights, **busday_kwargs
    ):
        self._bushours_dict = bushours_dict
        self._calendar_days = calendar_days
        self._calendar_cumulative = cumulative
        self._weights = weights
        self._busday_kwargs = busday_kwargs
        super().__init__()


class BusdayTransform(_BusdayTransformBase):
    """Forward transform: matplotlib date numbers -> business-day floats.

    Maps each matplotlib date number (float, days since epoch) to a
    weighted business-day float: integer part corresponds to the
    cumulative weighted business-day index, while the fractional
    part represents the normalised position within the active session.
    """

    def transform_non_affine(self, x):
        x = np.asarray(x)
        # num2date returns tz-aware datetimes; strip tzinfo before numpy conversion
        dates = [d.replace(tzinfo=None) for d in mdates.num2date(x.ravel())]
        result = _datetime_to_busday_float(
            dates,
            self._bushours_dict,
            self._calendar_days,
            self._calendar_cumulative,
            self._weights,
            **self._busday_kwargs,
        )
        return result.reshape(x.shape)

    def inverted(self):
        return InvertedBusdayTransform(
            self._bushours_dict,
            self._calendar_days,
            self._calendar_cumulative,
            self._weights,
            **self._busday_kwargs,
        )


class InvertedBusdayTransform(_BusdayTransformBase):
    """Inverse transform: business-day floats -> matplotlib date numbers.

    Not perfectly invertible: timestamps outside business hours were
    clipped to session boundaries during the forward transform.
    """

    def transform_non_affine(self, x):
        x = np.asarray(x, dtype=float)
        dates = _busday_float_to_datetime(
            x.ravel(),
            self._bushours_dict,
            self._calendar_days,
            self._calendar_cumulative,
            self._weights,
        )
        return mdates.date2num(dates).reshape(x.shape)

    def inverted(self):
        return BusdayTransform(
            self._bushours_dict,
            self._calendar_days,
            self._calendar_cumulative,
            self._weights,
            **self._busday_kwargs,
        )


class BusdayScale(mscale.ScaleBase):
    """Matplotlib scale that compresses off-hours and non-business days.

    Maps datetime values to business-day coordinates. Days and hours outside
    the defined schedule are collapsed so that every visible unit on the axis
    corresponds to active time.

    Parameters
    ----------
    axis : matplotlib.axis.Axis
        The axis this scale is attached to.
    bushours : tuple, list of 7 tuples, or dict, optional
        Active hours per weekday (hours as floats, 0–24). Three forms:

        ``(start, end)``
            Same session for all days (e.g. ``(9, 17)``). The weekmask still
            applies, so off-days (Sat/Sun by default) are collapsed regardless.
            Default ``(0, 24)``.

        list of 7 ``(start, end)``
            One pair per weekday Mon–Sun, fully explicit.

        dict ``{weekday: (start, end)}``
            Per-day overrides; keys are integers 0–6 or names
            ``"Mon"``–``"Sun"``. Defaults for unspecified days::

                | Day  | Key  | Default |
                | ---- | ---- | ------- |
                | Mon  | 0    | ``(0, 24)`` |
                | Tue  | 1    | ``(0, 24)`` |
                | Wed  | 2    | ``(0, 24)`` |
                | Thu  | 3    | ``(0, 24)`` |
                | Fri  | 4    | ``(0, 24)`` |
                | Sat  | 5    | ``(0, 0)``  |
                | Sun  | 6    | ``(0, 0)``  |

            The weekmask is derived automatically: days with non-zero hours
            are treated as business days, so passing ``{"Sun": (10, 18)}``
            will show Sundays without a separate *weekmask* override.

    weekmask : str, array-like, or None, optional
        Which weekdays are business days (``"1"`` = on, ``"0"`` = off).
        Passed to :func:`numpy.is_busday`. When ``None`` (default):

        - For dict / list-of-7 *bushours*: derived automatically — days with
          non-zero hours become business days.
        - For uniform ``(start, end)`` *bushours*: ``"1111100"`` (Mon–Fri).

    holidays : array-like or None, optional
        Extra non-business dates, regardless of *weekmask*. Passed to numpy
        busday functions. Default ``None``.
    busdaycal : numpy.busdaycalendar or None, optional
        Pre-built calendar. When set, *weekmask* and *holidays* are ignored.
        Default ``None``.

    Examples
    --------
    Compress weekends only (default)::

        ax.set_xscale("busday")

    Compress overnight gaps as well::

        ax.set_xscale("busday", bushours=(9, 17))

    Show Sundays with custom hours, hide Saturdays::

        ax.set_xscale("busday", bushours={"Sun": (10, 18)})

    Custom work-week with a holiday::

        ax.set_xscale("busday", weekmask="Sun Mon Tue Wed Thu",
                      holidays=["2025-01-01"])
    """

    name = "busday"

    def __init__(
        self,
        axis,
        bushours=(0, 24),
        weekmask=None,
        holidays=None,
        busdaycal=None,
    ):
        self._bushours_dict = _normalize_bushours(bushours)
        starts, ends = _bushours_bounds(self._bushours_dict)
        self._weights = ends - starts

        busday_kwargs = {}
        if busdaycal is not None:
            busday_kwargs["busdaycal"] = busdaycal
        else:
            if weekmask is None:
                # Per-day spec (dict or list of 7): derive weekmask from which days
                # have non-zero hours so callers don't need a separate weekmask arg.
                # Uniform (start, end) tuple: fall back to Mon–Fri default.
                is_per_day = isinstance(bushours, dict) or (
                    isinstance(bushours, (list, tuple)) and len(bushours) == 7
                )
                if is_per_day:
                    weekmask = "".join(
                        "1"
                        if self._bushours_dict[i][1] > self._bushours_dict[i][0]
                        else "0"
                        for i in range(7)
                    )
                else:
                    weekmask = "1111100"
            busday_kwargs["weekmask"] = weekmask
            if holidays is not None:
                busday_kwargs["holidays"] = holidays

        self._calendar_days, self._calendar_cumulative = _build_weighted_calendar(
            self._weights,
            **busday_kwargs,
        )

        self._busday_kwargs = busday_kwargs

        super().__init__(axis)

    def get_transform(self):
        return BusdayTransform(
            self._bushours_dict,
            self._calendar_days,
            self._calendar_cumulative,
            self._weights,
            **self._busday_kwargs,
        )

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
