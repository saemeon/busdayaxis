# Copyright (c) Simon Niederberger.
# Distributed under the terms of the Modified BSD License.

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

import matplotlib.dates as mdates
import numpy as np

if TYPE_CHECKING:
    from matplotlib.artist import Artist
    from matplotlib.axes import Axes


# ── holidays_from_exchange ────────────────────────────────────────────────────


def holidays_from_exchange(calendar, start, end) -> list[str]:
    """Return non-trading weekdays as ISO date strings for use with
    ``holidays=``.

    Extracts trading days from an ``exchange_calendars`` or
    ``pandas_market_calendars`` calendar object and returns all weekdays in
    ``[start, end]`` that are *not* trading days — i.e. the holidays and
    irregular closures you can pass directly to ``holidays=``.

    The function duck-types the calendar object and tries all known calling
    conventions, so no hard dependency on either library is introduced:
    ``pandas_market_calendars`` uses ``schedule(start_date=, end_date=)``,
    while ``exchange_calendars`` exposes ``sessions_in_range(start, end)``.

    Parameters
    ----------
    calendar : exchange_calendars or pandas_market_calendars calendar
        Any object that exposes a ``schedule()`` method returning a
        DataFrame whose index contains the trading dates.
    start, end : str or datetime-like
        Inclusive date range to scan (e.g. ``"2024-01-01"``).

    Returns
    -------
    list[str]
        ISO date strings (``"YYYY-MM-DD"``) of weekdays in ``[start, end]``
        that are not trading sessions.

    Examples
    --------
    With ``exchange_calendars``:

    ```python
    import exchange_calendars as xcals
    import busdayaxis

    cal = xcals.get_calendar("XNYS")
    holidays = busdayaxis.holidays_from_exchange(cal, "2025-01-01", "2025-12-31")
    ax.set_xscale("busday", holidays=holidays)
    ```

    With ``pandas_market_calendars``:

    ```python
    import pandas_market_calendars as mcal
    import busdayaxis

    cal = mcal.get_calendar("NYSE")
    holidays = busdayaxis.holidays_from_exchange(cal, "2025-01-01", "2025-12-31")
    ax.set_xscale("busday", holidays=holidays)
    ```
    """
    import pandas as pd

    start_s = pd.Timestamp(start).strftime("%Y-%m-%d")
    end_s = pd.Timestamp(end).strftime("%Y-%m-%d")

    # Try the known calling conventions in order:
    #   1. pandas_market_calendars: schedule(start_date=, end_date=) → DataFrame
    #   2. generic fallback:        schedule(start=, end=)            → DataFrame
    #   3. exchange_calendars:      sessions_in_range(start, end)     → DatetimeIndex
    trading_index = None
    for kwargs in (
        {"start_date": start_s, "end_date": end_s},
        {"start": start_s, "end": end_s},
    ):
        try:
            result = calendar.schedule(**kwargs)
            trading_index = result.index
            break
        except (TypeError, AttributeError):
            continue

    if trading_index is None:
        try:
            trading_index = calendar.sessions_in_range(start_s, end_s)
        except AttributeError:
            pass

    if trading_index is None:
        raise ValueError(
            "Could not extract trading sessions from the calendar object. "
            "Expected an exchange_calendars or pandas_market_calendars calendar."
        )

    trading_dates = {ts.date() for ts in trading_index}
    return [
        d.strftime("%Y-%m-%d")
        for d in pd.bdate_range(start_s, end_s)
        if d.date() not in trading_dates
    ]


# ── mark_gaps ─────────────────────────────────────────────────────────────────


def mark_gaps(
    ax: Axes,
    style: str = "vline",
    **kwargs,
) -> list[Artist]:
    """Mark session-boundary gaps on a ``"busday"``-scale axis.

    Draws a visual indicator at every point where the axis collapses a gap
    (end of a session, overnight, weekend, holiday). Useful for signalling
    to the reader that time has been removed.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Axis that must already use the ``"busday"`` scale.
    style : {"vline", "broken", "both"}, default ``"vline"``
        Visual style:

        - ``"vline"`` — a thin vertical line at each seam.
        - ``"broken"`` — two diagonal slash marks at the top and bottom of
          the axes at each seam (traditional broken-axis convention).
        - ``"both"`` — vline and broken marks combined.
    **kwargs
        Forwarded to the underlying artists. Useful keys:

        - ``color`` (default ``"gray"`` for vline, ``"k"`` for broken)
        - ``linewidth`` (default ``0.8`` for vline, ``1.5`` for broken)
        - ``linestyle`` — vline only (default ``"--"``)
        - ``alpha``
        - ``zorder``
        - ``size`` — broken only, size of the slash marks in points
          (default ``10``)

    Returns
    -------
    list of matplotlib artists
        All artists added to the axes, so the caller can adjust them later.

    Examples
    --------

    ```python
    ax.set_xscale("busday", bushours=(9, 17))
    busdayaxis.mark_gaps(ax)                          # thin dashed vlines
    busdayaxis.mark_gaps(ax, style="broken")          # slash marks only
    busdayaxis.mark_gaps(ax, style="both", color="steelblue", alpha=0.4)
    ```
    """
    from ._scale import BusdayScale

    if style not in ("vline", "broken", "both"):
        raise ValueError(f"style must be 'vline', 'broken', or 'both', got {style!r}")

    scale = ax.xaxis._scale
    if not isinstance(scale, BusdayScale):
        raise ValueError(
            "ax must use the 'busday' scale; call ax.set_xscale('busday', ...) first."
        )

    gap_positions = _find_gap_positions(ax, scale)
    if not gap_positions:
        return []

    artists: list[Artist] = []

    if style in ("vline", "both"):
        kw: dict = {"color": "gray", "linewidth": 0.8, "linestyle": "--"}
        kw.update({k: v for k, v in kwargs.items() if k != "size"})
        for x in gap_positions:
            artists.append(ax.axvline(x=x, **kw))

    if style in ("broken", "both"):
        size = kwargs.get("size", 10)
        kw = {k: v for k, v in kwargs.items() if k not in ("size", "linestyle", "ls")}
        kw.setdefault("color", "k")
        kw.setdefault("linewidth", 1.5)
        for x in gap_positions:
            artists.extend(_draw_broken_marks(ax, x, size=size, **kw))

    return artists


def _find_gap_positions(ax: Axes, scale) -> list[float]:
    """Return sorted matplotlib-date-number positions of all session closes
    in the current view.

    ``ax.get_xlim()`` returns data coordinates (matplotlib date numbers),
    so gap positions are returned in the same space. The busday scale
    transform handles display positioning automatically.
    """
    vmin_mpl, vmax_mpl = ax.get_xlim()  # matplotlib date numbers (data coords)

    vmin_dt = mdates.num2date(vmin_mpl).replace(tzinfo=None)
    vmax_dt = mdates.num2date(vmax_mpl).replace(tzinfo=None)

    days = np.arange(
        np.datetime64(vmin_dt.date(), "D"),
        np.datetime64(vmax_dt.date(), "D") + np.timedelta64(1, "D"),
        dtype="datetime64[D]",
    )
    business_days = days[np.is_busday(days, **scale._busday_kwargs)]
    if len(business_days) == 0:
        return []

    weekdays = ((business_days.view("int64") + 3) % 7).astype(int)

    n = len(business_days)
    gap_positions: set[float] = set()
    for i, (day, wd) in enumerate(zip(business_days, weekdays)):
        intervals = scale._bushours_dict[wd]
        py_day = day.astype("datetime64[ms]").astype(object)
        for j, (_, e) in enumerate(intervals):
            close_dt = py_day + dt.timedelta(hours=e)
            is_last_interval = j == len(intervals) - 1

            # For end-of-day closes: skip if the next business day opens at the
            # exact same instant (e.g. Mon 24:00 == Tue 00:00 when bushours=(0,24)).
            if is_last_interval and i + 1 < n:
                next_wd = int(weekdays[i + 1])
                next_intervals = scale._bushours_dict[next_wd]
                if next_intervals:
                    next_day = business_days[i + 1]
                    py_next = next_day.astype("datetime64[ms]").astype(object)
                    next_open_dt = py_next + dt.timedelta(hours=next_intervals[0][0])
                    if close_dt == next_open_dt:
                        continue

            mpl_num = float(mdates.date2num(close_dt))
            if vmin_mpl <= mpl_num <= vmax_mpl:
                gap_positions.add(round(mpl_num, 10))

    return sorted(gap_positions)


def _draw_broken_marks(ax: Axes, x: float, size: float = 10, **kwargs) -> list[Artist]:
    """Draw diagonal slash marks at busday data coordinate *x*."""
    from matplotlib.transforms import blended_transform_factory

    kwargs.setdefault("clip_on", False)

    # Blended transform: x in data (busday) coords, y in axes fraction.
    trans = blended_transform_factory(ax.transData, ax.transAxes)

    # Marker: a diagonal slash. d controls the lean — 0.4 gives a clear
    # visual break without being too wide.
    d = 0.4
    marker = [(-1, -d), (1, d)]

    added: list[Artist] = []
    for y in (0.0, 1.0):
        (line,) = ax.plot(
            [x],
            [y],
            transform=trans,
            marker=marker,
            markersize=size,
            linestyle="none",
            **kwargs,
        )
        added.append(line)
    return added
