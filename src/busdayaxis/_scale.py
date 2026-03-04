# Copyright (c) Simon Niederberger.
# Distributed under the terms of the Modified BSD License.

import matplotlib.dates as mdates
import matplotlib.scale as mscale
import matplotlib.transforms as mtransforms
import numpy as np
import pandas as pd
from pandas.core.dtypes.common import is_nested_list_like

from busdayaxis._locator import BusdayLocator

EPOCH = np.datetime64("1970-01-01", "D")


def _validate_bushours(bushours):
    """Validate the business hour interval.

    The transform assumes a strictly positive interval inside the
    24 hour day. Invalid input would otherwise produce divisions by
    zero or inverted mappings.
    """
    if not isinstance(bushours, (tuple, list)) or len(bushours) != 2:
        raise ValueError("bushours must be a tuple (start_hour, end_hour).")

    start, end = bushours

    if not (0 <= start < end <= 24):
        raise ValueError("bushours must satisfy 0 <= start < end <= 24.")


def _datetime_to_busday_float(values, bushours=(0, 24), **busday_kwargs) -> np.ndarray:
    """Convert datetime-like values to business-day floats.

    Mapping:
        business_day_index + intraday_fraction

    Intraday fraction is defined only inside business hours. Times outside
    that interval are clipped to the boundaries so that nights collapse
    to the endpoints of the business session.
    """

    _validate_bushours(bushours)

    values = pd.DatetimeIndex(pd.to_datetime(values))

    day = values.floor("D")
    intraday_fraction = (values - day).total_seconds() / 86400.0

    bushour_start = bushours[0] / 24
    bushour_end = bushours[1] / 24

    # Clip timestamps to the business-hour interval so that off-hours
    # collapse to the session boundaries.
    intraday_fraction = np.clip(intraday_fraction, bushour_start, bushour_end)

    # Normalise the business-hour interval to [0, 1].
    intraday_fraction = (intraday_fraction - bushour_start) / (
        bushour_end - bushour_start
    )

    weekday = values.weekday

    # Roll weekends forward so that all weekend timestamps collapse
    # to Monday 00:00 in business time.
    rolled = day + pd.to_timedelta(
        np.where(weekday == 5, 2, np.where(weekday == 6, 1, 0)), unit="D"
    )

    business_days = np.busday_count(
        EPOCH, rolled.values.astype("datetime64[D]"), **busday_kwargs
    ).astype(float)

    # Weekend timestamps collapse to the beginning of the business day.
    intraday = np.where(weekday >= 5, 0.0, intraday_fraction)

    return business_days + intraday


def _busday_float_to_datetime(
    values, bushours=(0, 24), **busday_kwargs
) -> pd.DatetimeIndex:
    """Convert business-day floats back to datetime values.

    Note that the transform is not perfectly invertible because
    timestamps outside business hours are clipped during the forward
    transformation.
    """

    _validate_bushours(bushours)

    values = np.asarray(values, dtype=float)

    day_int = np.floor(values).astype(int)

    date = np.busday_offset(
        EPOCH,
        day_int,
        roll="forward",
        **busday_kwargs,
    ).astype("datetime64[s]")

    intraday_fraction = values - day_int

    bushour_start = bushours[0] / 24
    bushour_end = bushours[1] / 24

    # Reverse the intraday normalisation.
    intraday_fraction = (
        intraday_fraction * (bushour_end - bushour_start) + bushour_start
    )

    intraday_seconds = (
        (intraday_fraction * 86400.0).astype("int64").astype("timedelta64[s]")
    )

    datetime = date + intraday_seconds

    return pd.to_datetime(datetime)


class BusdayTransform(mtransforms.Transform):
    """Forward transform:
    matplotlib date numbers -> business-time floats
    """

    input_dims = 1
    output_dims = 1
    is_separable = True

    def __init__(self, bushours=(0, 24), **busday_kwargs):
        _validate_bushours(bushours)
        self._bushours = bushours
        self._busday_kwargs = busday_kwargs
        super().__init__()

    def transform_non_affine(self, x):
        """
        Convert matplotlib date numbers (days since 1970-01-01)
        to business-day floats.
        """

        dates = mdates.num2date(x)

        if is_nested_list_like(dates):
            return [
                _datetime_to_busday_float(
                    d,
                    bushours=self._bushours,
                    **self._busday_kwargs,
                )
                for d in dates
            ]

        return _datetime_to_busday_float(
            dates,
            bushours=self._bushours,
            **self._busday_kwargs,
        )

    def inverted(self):
        return InvertedBusdayTransform(
            bushours=self._bushours,
            **self._busday_kwargs,
        )


class InvertedBusdayTransform(mtransforms.Transform):
    """Inverse transform:
    business-time floats -> matplotlib date numbers
    """

    input_dims = 1
    output_dims = 1
    is_separable = True

    def __init__(self, bushours=(0, 24), **busday_kwargs):
        _validate_bushours(bushours)
        self._bushours = bushours
        self._busday_kwargs = busday_kwargs
        super().__init__()

    def transform_non_affine(self, x):
        x = np.atleast_1d(np.asarray(x, dtype=float))

        dates = _busday_float_to_datetime(
            x,
            bushours=self._bushours,
            **self._busday_kwargs,
        )

        return mdates.date2num(dates)

    def inverted(self):
        return BusdayTransform(
            bushours=self._bushours,
            **self._busday_kwargs,
        )


class BusdayScale(mscale.ScaleBase):
    name = "busday"

    def __init__(self, axis, bushours=(0, 24), **busday_kwargs):
        _validate_bushours(bushours)
        self._bushours = bushours
        self._busday_kwargs = busday_kwargs.copy()
        super().__init__(axis)

    def get_transform(self):
        return BusdayTransform(
            bushours=self._bushours,
            **self._busday_kwargs,
        )

    def set_default_locators_and_formatters(self, axis):
        axis._busday_kwargs = self._busday_kwargs.copy()
        axis._bushours = self._bushours

        majloc = BusdayLocator(base_locator=mdates.AutoDateLocator())
        majloc.set_axis(axis)

        majfmt = mdates.AutoDateFormatter(majloc.base_locator)

        axis.set_major_locator(majloc)
        axis.set_major_formatter(majfmt)

    def limit_range_for_scale(self, vmin, vmax, minpos):
        return vmin, vmax


def register_scale():
    mscale.register_scale(BusdayScale)
