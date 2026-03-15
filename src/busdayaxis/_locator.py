# Copyright (c) Simon Niederberger.
# Distributed under the terms of the Modified BSD License.

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, Sequence

import matplotlib.dates as mdates
import numpy as np

if TYPE_CHECKING:
    from typing import Union

    from matplotlib.axis import Axis
    from matplotlib.projections.polar import _AxisWrapper
    from matplotlib.ticker import _DummyAxis
    from numpy.typing import NDArray

    AxisLike = Union[Axis, _DummyAxis, _AxisWrapper, None]

_DEFAULT_BUSHOURS = {i: (0, 24) for i in range(7)}


class BusdayLocator(mdates.DateLocator):
    """Tick locator that filters out ticks outside business hours and business days.

    Wraps any Matplotlib date locator and discards ticks that fall on
    non-business days or outside the active session defined by ``bushours``.

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
    keep_midnight_ticks : bool or None, optional
        Controls whether ticks at midnight (00:00) on business days are kept
        even when they fall outside ``bushours``. When ``None`` (default), this
        is determined automatically: midnight ticks are kept for
        daily-granularity locators (e.g. ``DayLocator``) so that day labels
        remain properly aligned, and suppressed for finer locators (e.g.
        ``HourLocator``) where they would appear outside the visible session.

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
        keep_midnight_ticks: bool | None = None,
    ) -> None:
        self.base_locator = base_locator or mdates.AutoDateLocator()
        self._keep_midnight_ticks = keep_midnight_ticks

    def set_axis(self, axis: AxisLike) -> None:
        super().set_axis(axis)
        self.base_locator.set_axis(axis)

    def _filter_ticks(
        self, ticks: NDArray[np.float64] | Sequence[float]
    ) -> Sequence[float]:
        ticks_arr = np.asarray(ticks, dtype=float)
        if len(ticks_arr) == 0:
            return []

        dts = np.array([mdates.num2date(t).replace(tzinfo=None) for t in ticks_arr])

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

        return ticks_arr[busday_mask & bushour_mask].tolist()

    def __call__(self) -> Sequence[float]:
        return self._filter_ticks(self.base_locator())

    def set_tzinfo(self, tz: dt.tzinfo | None) -> None:
        self.base_locator.set_tzinfo(tz)

    def datalim_to_dt(self) -> tuple[dt.datetime, dt.datetime]:
        return self.base_locator.datalim_to_dt()

    def viewlim_to_dt(self) -> tuple[dt.datetime, dt.datetime]:
        return self.base_locator.viewlim_to_dt()

    def _get_unit(self):
        return self.base_locator._get_unit()

    def _get_interval(self):
        return self.base_locator._get_interval()

    def nonsingular(self, vmin, vmax):
        return self.base_locator.nonsingular(vmin, vmax)

    def tick_values(self, vmin: float, vmax: float) -> Sequence[float]:
        return self._filter_ticks(self.base_locator.tick_values(vmin, vmax))


class AutoDateLocator(BusdayLocator):
    def __init__(self, keep_midnight_ticks: bool | None = None, **kwargs) -> None:
        """Business-day-aware wrapper around `matplotlib.dates.AutoDateLocator`.

        All keyword arguments are forwarded to `~matplotlib.dates.AutoDateLocator`.
        """
        super().__init__(mdates.AutoDateLocator(**kwargs), keep_midnight_ticks)


class WeekdayLocator(BusdayLocator):
    def __init__(self, keep_midnight_ticks: bool | None = None, **kwargs) -> None:
        """Business-day-aware wrapper around `matplotlib.dates.WeekdayLocator`.

        Places ticks on specified weekdays, then discards any that fall on
        non-business days (e.g. public holidays). Midnight ticks are always kept
        because weekday ticks are placed at day boundaries.

        All keyword arguments are forwarded to `~matplotlib.dates.WeekdayLocator`.
        """
        super().__init__(mdates.WeekdayLocator(**kwargs), keep_midnight_ticks)


class DayLocator(BusdayLocator):
    def __init__(self, keep_midnight_ticks: bool | None = None, **kwargs) -> None:
        """Business-day-aware wrapper around `matplotlib.dates.DayLocator`.

        Places one tick per day (or every *interval* days), then discards any that
        fall on non-business days. Midnight ticks are always kept because daily
        ticks are placed at day boundaries.

        All keyword arguments are forwarded to `~matplotlib.dates.DayLocator`.
        """
        super().__init__(mdates.DayLocator(**kwargs), keep_midnight_ticks)


class HourLocator(BusdayLocator):
    def __init__(self, keep_midnight_ticks: bool | None = None, **kwargs) -> None:
        """Business-day-aware wrapper around `matplotlib.dates.HourLocator`.

        Places ticks at the specified hours, then discards any that fall outside
        business days or business hours. Midnight ticks are not kept by default
        because hourly ticks are sub-daily.

        All keyword arguments are forwarded to `~matplotlib.dates.HourLocator`.
        """
        super().__init__(mdates.HourLocator(**kwargs), keep_midnight_ticks)


class MinuteLocator(BusdayLocator):
    def __init__(self, keep_midnight_ticks: bool | None = None, **kwargs) -> None:
        """Business-day-aware wrapper around `matplotlib.dates.MinuteLocator`.

        Places ticks at the specified minutes, then discards any that fall outside
        business days or business hours. Midnight ticks are not kept by default
        because minute-level ticks are sub-daily.

        All keyword arguments are forwarded to `~matplotlib.dates.MinuteLocator`.
        """
        super().__init__(mdates.MinuteLocator(**kwargs), keep_midnight_ticks)


class SecondLocator(BusdayLocator):
    def __init__(self, keep_midnight_ticks: bool | None = None, **kwargs) -> None:
        """Business-day-aware wrapper around `matplotlib.dates.SecondLocator`.

        Places ticks at the specified seconds, then discards any that fall outside
        business days or business hours. Midnight ticks are not kept by default
        because second-level ticks are sub-daily.

        All keyword arguments are forwarded to `~matplotlib.dates.SecondLocator`.
        """
        super().__init__(mdates.SecondLocator(**kwargs), keep_midnight_ticks)


class MicrosecondLocator(BusdayLocator):
    def __init__(self, keep_midnight_ticks: bool | None = None, **kwargs) -> None:
        """Business-day-aware wrapper around `matplotlib.dates.MicrosecondLocator`.

        Places ticks at the specified microseconds, then discards any that fall
        outside business days or business hours. Midnight ticks are not kept by
        default because microsecond-level ticks are sub-daily.

        All keyword arguments are forwarded to `~matplotlib.dates.MicrosecondLocator`.
        """
        super().__init__(mdates.MicrosecondLocator(**kwargs), keep_midnight_ticks)


class MidBusdayLocator(mdates.DateLocator):
    """Places one tick at the midpoint of the business hours for each business day.

    Useful for centering day labels within each session, even when business
    hours vary by weekday or differ from the standard 9–17 window.

    Examples
    --------
    Center day labels as minor ticks::

        ax.set_xscale("busday", bushours=(9, 17))
        ax.xaxis.set_minor_locator(busdayaxis.MidBusdayLocator())
        ax.xaxis.set_minor_formatter(mdates.DateFormatter("%a"))
    """

    def __call__(self) -> Sequence[float]:
        if self.axis is None:
            return []
        vmin, vmax = self.axis.get_view_interval()
        return self.tick_values(vmin, vmax)

    def tick_values(self, vmin: float, vmax: float) -> Sequence[float]:
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
            return []

        bushours_dict = getattr(self.axis, "_bushours", _DEFAULT_BUSHOURS)
        weekday = (busdays.view("int64") + 3) % 7  # epoch (1970-01-01) was Thursday = 3

        _starts = np.array([bushours_dict[i][0] for i in range(7)])
        _ends = np.array([bushours_dict[i][1] for i in range(7)])
        mid_fracs = (_starts[weekday] + _ends[weekday]) / 2 / 24

        busday_nums = mdates.date2num(busdays.astype("datetime64[ms]").astype(object))

        return np.asarray(busday_nums + mid_fracs, dtype=float).tolist()
