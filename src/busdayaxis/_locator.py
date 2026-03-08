# Copyright (c) Simon Niederberger.
# Distributed under the terms of the Modified BSD License.

from __future__ import annotations

import matplotlib.dates as mdates
import numpy as np
from matplotlib.axis import Axis

_DEFAULT_BUSHOURS = {i: (0, 24) for i in range(7)}


class BusdayLocator(mdates.DateLocator):
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

    def __init__(
        self,
        base_locator: mdates.DateLocator | None = None,
        keep_midnight_ticks=None,
    ) -> None:
        self.base_locator = base_locator or mdates.AutoDateLocator()
        self._keep_midnight_ticks = keep_midnight_ticks

    def set_axis(self, axis: Axis) -> None:
        super().set_axis(axis)
        self.base_locator.set_axis(axis)

    def _filter_ticks(self, ticks) -> np.ndarray:
        ticks = np.asarray(ticks)
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
        if self._keep_midnight_ticks is None:
            # allow midnight ticks through so daily-granularity ticks (placed at 00:00
            # by AutoDateLocator) are not filtered by the business-hours check
            keep_midnight_ticks = self.base_locator._get_unit() >= 1
        else:
            keep_midnight_ticks = self._keep_midnight_ticks

        if keep_midnight_ticks:
            day_start = frac < 1e-9
            bushour_mask = within_hours | day_start
        else:
            bushour_mask = within_hours

        return ticks[busday_mask & bushour_mask]

    def __call__(self) -> np.ndarray:
        return self._filter_ticks(self.base_locator())

    def set_tzinfo(self, tz):
        self.base_locator.set_tzinfo(tz)

    def datalim_to_dt(self):
        return self.base_locator.datalim_to_dt()

    def viewlim_to_dt(self):
        return self.base_locator.viewlim_to_dt()

    def _get_unit(self):
        return self.base_locator._get_unit()

    def _get_interval(self):
        return self.base_locator._get_interval()

    def nonsingular(self, vmin, vmax):
        return self.base_locator.nonsingular(vmin, vmax)

    def tick_values(self, vmin: float, vmax: float) -> np.ndarray:
        return self._filter_ticks(self.base_locator.tick_values(vmin, vmax))


class MidBusdayLocator(mdates.DateLocator):
    """Places one tick at the midpoint of business hours for each business day.

    Useful for centering day labels within each session, even when business
    hours vary by weekday or differ from the standard 9–17 window.

    Examples
    --------
    Center day labels as minor ticks::

        ax.set_xscale("busday", bushours=(9, 17))
        ax.xaxis.set_minor_locator(busdayaxis.MidBusdayLocator())
        ax.xaxis.set_minor_formatter(mdates.DateFormatter("%a"))
    """

    def __call__(self) -> np.ndarray:
        vmin, vmax = self.axis.get_view_interval()
        return self.tick_values(vmin, vmax)

    def tick_values(self, vmin: float, vmax: float) -> np.ndarray:
        dt_min = mdates.num2date(vmin).replace(tzinfo=None)
        dt_max = mdates.num2date(vmax).replace(tzinfo=None)

        days = np.arange(
            np.datetime64(dt_min.date(), "D"),
            np.datetime64(dt_max.date(), "D") + np.timedelta64(1, "D"),
            dtype="datetime64[D]",
        )

        busday_kwargs = getattr(self.axis, "_busday_kwargs", {})
        busdays = days[np.is_busday(days, **busday_kwargs)]

        if len(busdays) == 0:
            return np.array([])

        bushours_dict = getattr(self.axis, "_bushours", _DEFAULT_BUSHOURS)
        weekday = (busdays.view("int64") + 3) % 7  # epoch (1970-01-01) was Thursday = 3

        _starts = np.array([bushours_dict[i][0] for i in range(7)])
        _ends = np.array([bushours_dict[i][1] for i in range(7)])
        mid_fracs = (_starts[weekday] + _ends[weekday]) / 2 / 24

        busday_nums = mdates.date2num(busdays.astype("datetime64[ms]").astype(object))

        return busday_nums + mid_fracs
