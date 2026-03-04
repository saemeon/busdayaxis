# Copyright (c) Simon Niederberger.
# Distributed under the terms of the Modified BSD License.

import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import numpy as np


class BusdayLocator(mticker.Locator):
    """
    Wrap a datetime locator and remove ticks that fall outside
    business days or outside business hours.

    Parameters
    ----------
    base_locator : matplotlib.ticker.Locator
        Any datetime-based locator (e.g. AutoDateLocator)
    """

    def __init__(self, base_locator=None):
        self.base_locator = base_locator or mdates.AutoDateLocator()

    def set_axis(self, axis):
        super().set_axis(axis)
        self.base_locator.set_axis(axis)

    def _get_unit(self):
        return self.base_locator._get_unit()

    def __call__(self):
        ticks = self.base_locator()

        if len(ticks) == 0:
            return ticks

        dts = np.asarray(mdates.num2date(ticks))
        dts = np.array([dt.replace(tzinfo=None) for dt in dts])

        days = np.array(dts, dtype="datetime64[D]")

        busday_kwargs = getattr(self.axis, "_busday_kwargs", {})
        busday_mask = np.is_busday(days, **busday_kwargs)

        # Business hour mask using full timestamp precision
        frac = np.array(
            [
                (dt.hour * 3600 + dt.minute * 60 + dt.second + dt.microsecond / 1e6)
                / 86400.0
                for dt in dts
            ]
        )

        bushours = getattr(self.axis, "_bushours", (0, 24))
        bushour_start = bushours[0] / 24
        bushour_end = bushours[1] / 24

        # Keep ticks that fall within business hours, additionally keeping day start (00:00)
        bushour_mask = ((frac >= bushour_start) & (frac < bushour_end)) | (frac == 0)

        return np.asarray(ticks)[busday_mask & bushour_mask]
