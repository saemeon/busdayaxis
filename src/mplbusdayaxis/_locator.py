# Copyright (c) Simon Niederberger.
# Distributed under the terms of the Modified BSD License.

import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import numpy as np


class BusdayLocator(mticker.Locator):
    """
    Wrap an arbitrary datetime locator and remove
    ticks that fall on non-business days.

    Parameters
    ----------
    base_locator : matplotlib.ticker.Locator
        Any datetime-based locator (e.g. AutoDateLocator)
    busday_kwargs :
        Passed to np.is_busday (e.g. weekmask, holidays)
    """

    def __init__(self, base_locator=None):
        if base_locator is None:
            base_locator = mticker.MultipleLocator(1)
        self.base_locator = base_locator

    def set_axis(self, axis):
        super().set_axis(axis)
        self.base_locator.set_axis(axis)

    def __call__(self):
        ticks = self.base_locator()

        if len(ticks) == 0:
            return ticks

        busday_kwargs = getattr(self.axis, "_busday_kwargs", {})

        dts = mdates.num2date(ticks)
        days = np.array([np.datetime64(dt.replace(tzinfo=None), "D") for dt in dts])
        mask = np.is_busday(days, **busday_kwargs)
        return np.asarray(ticks)[mask]
