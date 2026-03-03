import matplotlib.dates as mdates
import matplotlib.scale as mscale
import matplotlib.transforms as mtransforms
import numpy as np
import pandas as pd
from pandas.core.dtypes.common import is_nested_list_like

from mplbusdayaxis._locator import BusdayLocator

EPOCH = np.datetime64("1970-01-01", "D")


def _datetime_to_busday_float(values, **busday_kwargs) -> np.ndarray:
    """Convert datetime-like values to business-day floats."""

    values = pd.DatetimeIndex(pd.to_datetime(values))

    day = values.floor("D")
    intraday = (values - day).total_seconds() / 86400.0

    weekday = values.weekday
    rolled = day + pd.to_timedelta(
        np.where(weekday == 5, 2, np.where(weekday == 6, 1, 0)), unit="D"
    )

    business_days = np.busday_count(
        EPOCH, rolled.values.astype("datetime64[D]"), **busday_kwargs
    ).astype(float)

    intraday = np.where(weekday >= 5, 0.0, intraday)

    return business_days + intraday


def _busday_float_to_datetime(values, **busday_kwargs) -> pd.DatetimeIndex:
    """Convert business-day floats back to datetime-like values."""

    values = np.asarray(values, dtype=float)

    day_int = np.floor(values).astype(int)
    date = np.busday_offset(EPOCH, day_int, roll="forward", **busday_kwargs).astype(
        "datetime64[s]"
    )

    intraday_frac = values - day_int
    intraday_seconds = (
        (intraday_frac * 86400.0).astype("int64").astype("timedelta64[s]")
    )

    datetime = date + intraday_seconds

    return pd.to_datetime(datetime)


class BusdayTransform(mtransforms.Transform):
    """Transform for business time.

    Forward transform (float days -> business float)
    """

    input_dims = 1
    output_dims = 1
    is_separable = True
    _busday_kwargs = {}

    def __init__(self, **busday_kwargs):
        self._busday_kwargs = busday_kwargs
        super().__init__()

    def transform_non_affine(self, x):
        """
        Convert matplotlib date numbers (days since 1970-01-01) to business-day floats.

        Rules:
            - Monday..Friday increase linearly
            - Fractional part represents fraction of 24h
            - Saturday/Sunday collapse to Monday 00:00
        """
        dates = mdates.num2date(x)

        if is_nested_list_like(dates):
            return [_datetime_to_busday_float(d, **self._busday_kwargs) for d in dates]
        else:
            return _datetime_to_busday_float(dates, **self._busday_kwargs)

    def inverted(self):
        return InvertedBusdayTransform(**self._busday_kwargs)


class InvertedBusdayTransform(mtransforms.Transform):
    """Inverse transform (business float -> matplotlib date numbers)"""

    input_dims = 1
    output_dims = 1
    is_separable = True
    _busday_kwargs = {}

    def __init__(self, **busday_kwargs):
        self._busday_kwargs = busday_kwargs
        super().__init__()

    def transform_non_affine(self, x):
        x = np.atleast_1d(np.asarray(x, dtype=float))
        dates = _busday_float_to_datetime(x, **self._busday_kwargs)
        result = mdates.date2num(dates)
        return result

    def inverted(self):
        return BusdayTransform(**self._busday_kwargs)


class BusdayScale(mscale.ScaleBase):
    name = "busday"
    _busday_kwargs = {}

    def __init__(self, axis, **kwargs):
        self._busday_kwargs = kwargs.copy()
        super().__init__(axis)

    def get_transform(self):
        return BusdayTransform(**self._busday_kwargs)

    def set_default_locators_and_formatters(self, axis):
        axis._busday_kwargs = self._busday_kwargs.copy()
        majloc = BusdayLocator()
        majloc.set_axis(axis)
        majfmt = mdates.DateFormatter("%Y-%m-%d")
        axis.set_major_locator(majloc)
        axis.set_major_formatter(majfmt)

    def limit_range_for_scale(self, vmin, vmax, minpos):
        return vmin, vmax


def register_scale():
    mscale.register_scale(BusdayScale)
