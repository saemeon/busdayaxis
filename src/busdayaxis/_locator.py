# Copyright (c) Simon Niederberger.
# Distributed under the terms of the Modified BSD License.

from __future__ import annotations

import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import numpy as np
from matplotlib.axis import Axis

_DEFAULT_BUSHOURS = {i: (0, 24) for i in range(7)}


class BusdayLocator(mticker.Locator):
    """Tick locator that filters out ticks outside business hours and business days.

    Wraps any Matplotlib date locator and discards ticks that fall on
    non-business days or outside the active session defined by ``bushours``.
    Midnight ticks (00:00) on business days are always kept so that
    daily-granularity locators (e.g. ``DayLocator``) continue to work.

    The locator reads the business-hours and weekmask configuration from the
    axis automatically (set by ``BusdayScale``), so it stays in sync with the
    scale without any extra configuration.

    ``BusdayLocator`` is set automatically when you call
    ``ax.set_xscale("busday")``.

    Parameters
    ----------
    base_locator : matplotlib.dates.DateLocator, optional
        The underlying datetime locator that proposes tick candidates.
        If None, falls back to ``AutoDateLocator``.

    Examples
    --------
    Hourly ticks during business hours (9–17)::

        ax.set_xscale("busday", bushours=(9, 17))
        ax.xaxis.set_major_locator(
            BusdayLocator(mdates.HourLocator())
        )

    Daily ticks on business days only::

        ax.xaxis.set_major_locator(BusdayLocator(mdates.DayLocator()))
    """

    def __init__(self, base_locator: mdates.DateLocator | None = None) -> None:
        self.base_locator = base_locator or mdates.AutoDateLocator()

    def set_axis(self, axis: Axis) -> None:
        super().set_axis(axis)
        self.base_locator.set_axis(axis)

    def _get_unit(self) -> float:
        return self.base_locator._get_unit()

    def __call__(self) -> np.ndarray:
        ticks = self.base_locator()

        if len(ticks) == 0:
            return ticks

        dts = np.array([mdates.num2date(t).replace(tzinfo=None) for t in ticks])

        days = dts.astype("datetime64[D]")

        busday_kwargs = getattr(self.axis, "_busday_kwargs", {})
        busday_mask = np.is_busday(days, **busday_kwargs)

        weekday = (days.view("int64") + 3) % 7  # epoch (1970-01-01) was Thursday = 3
        intraday_s = (dts.astype("datetime64[s]") - days.astype("datetime64[s]")).view(
            "int64"
        )
        frac = intraday_s / 86400.0

        bushours_dict = getattr(self.axis, "_bushours", _DEFAULT_BUSHOURS)

        _starts = np.array([bushours_dict[i][0] for i in range(7)]) / 24
        _ends = np.array([bushours_dict[i][1] for i in range(7)]) / 24
        bushour_starts = _starts[weekday]
        bushour_ends = _ends[weekday]

        within_hours = (frac >= bushour_starts) & (frac < bushour_ends)
        # allow midnight ticks through so daily-granularity ticks (placed at 00:00
        # by AutoDateLocator) are not filtered by the business-hours check
        day_start = frac == 0

        bushour_mask = within_hours | day_start

        return np.asarray(ticks)[busday_mask & bushour_mask]
