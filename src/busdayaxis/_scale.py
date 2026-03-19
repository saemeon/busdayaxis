# Copyright (c) Simon Niederberger.
# Distributed under the terms of the Modified BSD License.

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, Mapping, Protocol, Sequence, Union, cast

import matplotlib.dates as mdates
import matplotlib.scale as mscale
import matplotlib.transforms as mtransforms
import numpy as np

if TYPE_CHECKING:
    from matplotlib.axis import Axis
    from numpy.typing import ArrayLike, NDArray

from busdayaxis._locator import AutoDateLocator, BusdayLocator

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
WEEKDAYS_MAP = {name: i for i, name in enumerate(WEEKDAYS)}

HourValue = Union[int, float, str, dt.time]
WeekdayKey = Union[str, int]

#####################################################################
# Helper functions
#####################################################################


def _to_hour_float(v: HourValue) -> float:
    if isinstance(v, str):
        v = dt.time.fromisoformat(v)
    if isinstance(v, dt.time):
        return v.hour + v.minute / 60 + v.second / 3600 + v.microsecond / 3_600_000_000
    return float(v)


def _is_single_interval(v: object) -> bool:
    return (
        isinstance(v, tuple)
        and len(v) == 2
        and all(isinstance(x, (int, float, str, dt.time)) for x in v)
    )


def _coerce_intervals(v: object, *, label: str = "hours") -> list[tuple[float, float]]:
    """Normalize a single ``(start, end)`` tuple or list of such tuples into
    a sorted, non-overlapping list of ``(start_float, end_float)`` pairs."""
    if _is_single_interval(v):
        v = cast(tuple[HourValue, HourValue], v)
        s, e = _to_hour_float(v[0]), _to_hour_float(v[1])
        if not (0 <= s <= e <= 24):
            raise ValueError(
                f"{label}: 0 <= start <= end <= 24 required, got ({s}, {e})"
            )
        return [(s, e)]
    if isinstance(v, (list, tuple)):
        result: list[tuple[float, float]] = []
        for i, item in enumerate(v):
            if not (isinstance(item, (list, tuple)) and len(item) == 2):
                raise ValueError(
                    f"{label}[{i}]: each interval must be a (start, end) pair, "
                    f"got {item!r}"
                )
            s = _to_hour_float(item[0])
            e = _to_hour_float(item[1])
            if not (0 <= s <= e <= 24):
                raise ValueError(
                    f"{label}[{i}]: 0 <= start <= end <= 24 required, got ({s}, {e})"
                )
            result.append((s, e))
        result.sort()
        for i in range(len(result) - 1):
            if result[i][1] > result[i + 1][0]:
                raise ValueError(
                    f"{label}: intervals must not overlap, "
                    f"got {result[i]} and {result[i + 1]}"
                )
        return result
    raise ValueError(
        f"{label}: expected (start, end) tuple or list of (start, end) pairs, got {v!r}"
    )


def _normalize_bushours(
    bushours: tuple[HourValue, HourValue]
    | Sequence[tuple[HourValue, HourValue]]
    | Mapping[
        WeekdayKey, tuple[HourValue, HourValue] | Sequence[tuple[HourValue, HourValue]]
    ],
) -> dict[int, list[tuple[float, float]]]:
    """Return a dict ``{0..6: [(start, end), ...]}`` from any supported bushours form.

    Accepted forms:

    - ``(start, end)``: single interval applied to all 7 days
    - ``[(start, end), ...]``: list of intervals applied to all 7 days
    - ``{weekday: (start, end) | [(start, end), ...]}``: per-day intervals;
      unspecified weekdays default to ``[(0, 24)]`` for Mon–Fri and ``[]`` for weekends
    """
    if isinstance(bushours, dict):
        int_dict: dict[int, list[tuple[float, float]]] = {}
        for k, v in bushours.items():
            if isinstance(k, str) and k in WEEKDAYS_MAP:
                weekday = WEEKDAYS_MAP[k]
            elif isinstance(k, int) and 0 <= k <= 6:
                weekday = k
            else:
                raise ValueError(f"Got {k!r}; expected int 0-6 or name in {WEEKDAYS}")
            int_dict[weekday] = _coerce_intervals(
                v, label=f"bushours for {WEEKDAYS[weekday]}"
            )
        # Unspecified weekdays: Mon–Fri full day, weekends closed
        return {i: int_dict.get(i, [] if i >= 5 else [(0.0, 24.0)]) for i in range(7)}

    # Uniform form: single (start, end) tuple or list of (start, end) tuples
    intervals = _coerce_intervals(bushours)
    return {i: intervals for i in range(7)}


def _total_durations(
    bushours_dict: dict[int, list[tuple[float, float]]],
) -> NDArray[np.float64]:
    """Return total active duration as a day-fraction (0–1) for each weekday."""
    return np.array([sum(e - s for s, e in bushours_dict[i]) / 24.0 for i in range(7)])


def _weekday_from_days(days_d64: NDArray[np.datetime64]) -> NDArray[np.int64]:
    """
    Compute weekday as 0=Mon, ..., 6=Sun for datetime64[D] arrays.

    1970-01-01 was a Thursday, which corresponds to weekday=3 in the
    Mon=0 convention.
    """
    return ((days_d64.view("int64") + 3) % 7).astype(int)


def _build_weighted_calendar(
    weights: NDArray[np.float64],
    **busday_kwargs,
) -> tuple[NDArray[np.datetime64], NDArray[np.float64]]:
    """Construct a lookup table mapping calendar days to cumulative
    weighted business-day coordinates."""

    # Cover the full datetime64[ns] representable range (~1678–2262).
    # Dates outside this range cannot be expressed as datetime64[ns] anyway,
    # so there is no value in extending further in either direction.
    days = np.arange(
        np.datetime64("1678-01-01", "D"),
        np.datetime64("2262-01-01", "D"),
        dtype="datetime64[D]",
    )

    weekday = _weekday_from_days(days)
    is_busday = np.is_busday(days, **busday_kwargs)

    day_weights = np.where(is_busday, weights[weekday], 0.0)
    cumulative = np.concatenate(([0.0], np.cumsum(day_weights)))

    # Anchor the representation to the matplotlib epoch (1970-01-01) so that
    # the busday float for 1970-01-01 is 0.0 and pre-1970 values are negative,
    # mirroring matplotlib's own date-number convention.
    epoch_idx = int((np.datetime64("1970-01-01", "D") - days[0]).astype(int))
    cumulative -= cumulative[epoch_idx]

    return days, cumulative


def _datetime_to_busday_float(
    values: ArrayLike,
    bushours_dict: dict[int, list[tuple[float, float]]],
    calendar_days: NDArray[np.datetime64],
    cumulative: NDArray[np.float64],
    weights: NDArray[np.float64],
    **busday_kwargs,
) -> NDArray[np.float64]:
    """Convert datetime-like values to business-day floats.

    Mapping:
        business_day_weighted_index + compressed_intraday

    The first part is a cumulative weighted index from a precomputed calendar
    table. The second part is the total elapsed active time within the day's
    session(s), computed as a piecewise-linear compression across all intervals:
    gaps between intervals (e.g. lunch breaks) are collapsed just like
    off-hours.
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

    # Piecewise compression: for each interval (s, e) sum up how much of it
    # has elapsed by intraday_fraction.  Gaps between intervals collapse to zero.
    # For each timestamp, compute how much active time has elapsed within the day.
    # Each interval (s, e) contributes min(max(t - s, 0), e - s): zero before the
    # interval starts, linear growth while inside it, and capped once past it.
    # Summing over all intervals gives the total compressed intraday offset.
    compressed = np.zeros_like(intraday_fraction)
    for wd in range(7):
        mask = weekday == wd
        if not np.any(mask):
            continue
        t = intraday_fraction[mask]
        c = np.zeros_like(t)
        for s, e in bushours_dict[wd]:
            s_f, e_f = s / 24.0, e / 24.0
            c += np.clip(t - s_f, 0.0, e_f - s_f)  # elapsed time within this interval
        compressed[mask] = c

    idx = (day - calendar_days[0]).astype(int)
    business_days = cumulative[idx]
    is_busday = np.is_busday(day, **busday_kwargs)
    intraday = np.where(is_busday, compressed, 0.0)
    busday_float = (business_days + intraday).astype(float)
    return busday_float


def _busday_float_to_datetime(
    values: ArrayLike,
    bushours_dict: dict[int, list[tuple[float, float]]],
    calendar_days: NDArray[np.datetime64],
    cumulative: NDArray[np.float64],
    weights: NDArray[np.float64],
) -> NDArray[np.datetime64]:
    """Convert business-day floats back to datetime values.

    Note that the transform is not perfectly invertible because timestamps
    outside business hours are clipped during the forward transformation.
    Times in gaps between intervals (e.g. lunch) map to the end of the
    preceding interval.
    """
    values = np.asarray(values, dtype=float)

    original_shape = values.shape
    values_flat = values.ravel()

    idx = np.searchsorted(cumulative, values_flat, side="right") - 1
    idx = np.clip(idx, 0, len(calendar_days) - 1)

    date_d = calendar_days[idx]
    weekday = _weekday_from_days(date_d)

    base = cumulative[idx]

    # scaled: day-fraction of wall-clock time within the session
    scaled = np.zeros_like(values_flat)
    for wd in range(7):
        mask = weekday == wd
        if not np.any(mask):
            continue
        intervals = bushours_dict[wd]
        if not intervals:
            scaled[mask] = 0.0
            continue
        # remaining: compressed active-time offset from start of this day
        remaining = values_flat[mask] - base[mask]
        result = np.full_like(remaining, intervals[-1][1] / 24.0)
        found = np.zeros(len(remaining), dtype=bool)
        for s, e in intervals:
            s_f, e_f = s / 24.0, e / 24.0
            dur = e_f - s_f
            in_this = (~found) & (remaining <= dur)
            result = np.where(in_this, s_f + remaining, result)
            found |= in_this
            remaining = np.where(~found, remaining - dur, remaining)
        scaled[mask] = result

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
        self,
        bushours_dict: dict[int, list[tuple[float, float]]],
        calendar_days: NDArray[np.datetime64],
        cumulative: NDArray[np.float64],
        weights: NDArray[np.float64],
        **busday_kwargs,
    ) -> None:
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

    def transform_non_affine(self, values: ArrayLike) -> ArrayLike:
        values = np.asarray(values)
        # num2date returns tz-aware datetimes; strip tzinfo before numpy conversion
        dates = [d.replace(tzinfo=None) for d in mdates.num2date(values.ravel())]
        result = _datetime_to_busday_float(
            dates,
            self._bushours_dict,
            self._calendar_days,
            self._calendar_cumulative,
            self._weights,
            **self._busday_kwargs,
        )
        return result.reshape(values.shape)

    def inverted(self) -> InvertedBusdayTransform:
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

    def transform_non_affine(self, values: ArrayLike) -> ArrayLike:
        values = np.asarray(values, dtype=float)
        dates = _busday_float_to_datetime(
            values.ravel(),
            self._bushours_dict,
            self._calendar_days,
            self._calendar_cumulative,
            self._weights,
        )
        return mdates.date2num(dates).reshape(values.shape)

    def inverted(self) -> BusdayTransform:
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

    Registered as the ``"busday"`` scale automatically on ``import busdayaxis``.
    All parameters below **except** ``axis`` can be passed directly to
    ``ax.set_xscale("busday", ...)``. ``axis`` is injected automatically by
    Matplotlib and must not be passed explicitly.

    Parameters
    ----------
    axis : matplotlib.axis.Axis
        Injected automatically by Matplotlib. Do not pass this via
        ``ax.set_xscale``.
    bushours : tuple[HourValue, HourValue]
                | list[tuple[HourValue, HourValue]]
                | Mapping[WeekdayKey, tuple[HourValue, HourValue]
                          | list[tuple[HourValue, HourValue]]]
                , optional
        Active hours per weekday. Gaps between intervals (e.g. a lunch break)
        are collapsed on the axis just like overnight gaps or weekends.

        ``HourValue`` is ``int | float | str | datetime.time``. Strings must
        be valid ISO time strings (e.g. ``"09:30"``). Numbers are hours since
        midnight (e.g. ``9.5`` = 09:30).
        ``WeekdayKey`` means either weekday index ``0..6`` or weekday name
        ``"Mon"``..``"Sun"``.

        Two accepted forms:

        - ``(start, end)`` or ``[(start, end), ...]``:
            One or more sessions applied uniformly to all days. A plain
            ``(start, end)`` tuple is shorthand for a single-element list.
            Intervals must be sorted and non-overlapping. The weekmask still
            applies, so off-days (Sat/Sun by default) are collapsed regardless.
            Default ``(0, 24)``.

            Example:

            ```python
            bushours=(9, 17)                    # numeric hours
            bushours=("09:00", "17:00")         # ISO time strings
            bushours=(dt.time(9), dt.time(17))  # datetime.time objects
            ```

            Multiple intervals — collapse a lunch break:

            ```python
            bushours=[(9, 12), (13, 17)]
            ```

            To apply also on weekends, use:

            ```python
            bushours=(9, 17), weekmask="1111111"  # Mon–Sun
            ```

        - ``Mapping[WeekdayKey, (start, end) | [(start, end), ...]]``:
            Per-day schedule; keys are integers ``0..6`` or names
            ``"Mon"``–``"Sun"``. Each value is either a single
            ``(start, end)`` tuple or a list of tuples.
            Defaults for unspecified days:

            | Day  | Key  | Default      |
            |------|------|--------------|
            | Mon  | 0    | `[(0, 24)]`  |
            | Tue  | 1    | `[(0, 24)]`  |
            | Wed  | 2    | `[(0, 24)]`  |
            | Thu  | 3    | `[(0, 24)]`  |
            | Fri  | 4    | `[(0, 24)]`  |
            | Sat  | 5    | `[]`         |
            | Sun  | 6    | `[]`         |

            The weekmask is derived automatically: days with at least one
            interval are treated as business days, so passing
            ``{"Sun": (10, 18)}`` includes Sundays without a separate
            *weekmask* override.

            Example:

            ```python
            bushours={"Sun": (10, 18)}  # Sundays with custom hours, weekdays 00-24
            ```

            Lunch break on Monday, early Friday close:

            ```python
            bushours={"Mon": [(9, 12), (13, 17)], "Fri": (9, 13)}
            ```

            FX Trading Hours:

            ```python
            bushours={
                "Sun": (22, 24),
                # Monday - Thursday 00:00-24:00
                "Fri": (0, 22),
            }
            ```

    weekmask : str, array-like, or None, optional
        Which weekdays are business days (``"1"`` = on, ``"0"`` = off).
        Passed to :func:`numpy.is_busday`. When ``None`` (default):

        - For dict *bushours*: derived automatically — days with at least one
          interval become business days.
        - For uniform *bushours* (tuple or list of tuples): ``"1111100"`` (Mon–Fri).

        Use a string of 7 characters (Mon–Sun), a space-separated list of
        three-letter day names, or any format accepted by ``numpy.is_busday``:

        ```python
        weekmask="1111100"              # Mon–Fri (default)
        weekmask="Mon Tue Wed Thu Fri"  # equivalent
        weekmask="Sun Mon Tue Wed Thu"  # Middle-Eastern work week
        weekmask="1111111"              # every day is a business day
        ```

    holidays : array-like or None, optional
        Extra non-business dates, regardless of *weekmask*. Dates on these
        days are collapsed to zero width on the axis, identical to weekends.
        Accepts any format understood by :func:`numpy.is_busday` (ISO strings,
        ``datetime.date``, ``numpy.datetime64``). Default ``None``.

        ```python
        holidays=["2025-01-01", "2025-12-25"]
        ```

    busdaycal : numpy.busdaycalendar or None, optional
        Pre-built calendar combining a weekmask and holiday list. When set,
        *weekmask* and *holidays* are ignored. Useful when reusing the same
        calendar across multiple axes. Default ``None``.

        Note that ``busdaycal`` only controls *which days* are business days;
        it does not affect *bushours*. The two parameters are independent.

        ```python
        cal = np.busdaycalendar(weekmask="Mon Tue Wed Thu Fri",
                                holidays=["2025-01-01"])
        ax.set_xscale("busday", busdaycal=cal)
        ```

    Notes
    -----
    - **Clipping:** Timestamps outside ``bushours`` are clipped to the nearest
      session boundary during the forward transform. For example, with
      ``bushours=(9, 17)``, both 08:30 and 09:00 map to the same axis
      position (the session open). With multiple intervals, times in a gap
      (e.g. during a lunch break) are clipped to the end of the preceding
      interval. The transform is therefore not perfectly invertible: the
      inverse always returns a time on a session boundary or within a session.
    - **Timezone handling:** The scale expects timezone-naive inputs and treats
      them as wall-clock time. If your data carries timezone info (e.g. a
      UTC-aware ``pandas.DatetimeIndex``), convert to the market's local
      timezone and strip the tzinfo before plotting::

          dates = dates_utc.tz_convert("America/New_York").tz_localize(None)

    Examples
    --------
    Compress weekends only (Mon–Fri default):

    ```python
    ax.set_xscale("busday")
    ```

    Compress overnight gaps as well as weekends:

    ```python
    ax.set_xscale("busday", bushours=(9, 17))
    ```

    Collapse a lunch break (12:00–13:00) in addition to overnight gaps:

    ```python
    ax.set_xscale("busday", bushours=[(9, 12), (13, 17)])
    ```

    Per-day hours — Friday early close, Monday with a lunch break:

    ```python
    ax.set_xscale("busday", bushours={"Mon": [(9, 12), (13, 17)], "Fri": (9, 13)})
    ```

    Show Sundays with custom hours; weekmask derived automatically (Sat excluded):

    ```python
    ax.set_xscale("busday", bushours={"Sun": (10, 18)})
    ```

    FX-style session: Sunday open 22:00, Friday close 22:00, full days otherwise:

    ```python
    ax.set_xscale("busday", bushours={"Sun": (22, 24), "Fri": (0, 22)})
    ```

    Middle-Eastern work week (Sun–Thu) with a holiday:

    ```python
    ax.set_xscale("busday", weekmask="Sun Mon Tue Wed Thu",
                  holidays=["2025-01-01"])
    ```

    Reuse a pre-built ``numpy.busdaycalendar``:

    ```python
    cal = np.busdaycalendar(weekmask="1111100", holidays=["2025-12-25"])
    ax.set_xscale("busday", busdaycal=cal)
    ```

    Custom tick placement with ``BusdayLocator``:

    ```python
    import matplotlib.dates as mdates
    ax.set_xscale("busday", bushours=(9, 17))
    ax.xaxis.set_major_locator(
        BusdayLocator(mdates.HourLocator(byhour=range(9, 18)))
    )
    ```
    """

    name = "busday"

    def __init__(
        self,
        axis: Axis,
        bushours: tuple[HourValue, HourValue]
        | Sequence[tuple[HourValue, HourValue]]
        | Mapping[
            WeekdayKey,
            tuple[HourValue, HourValue] | Sequence[tuple[HourValue, HourValue]],
        ] = (0, 24),
        weekmask: ArrayLike | None = None,
        holidays: ArrayLike | Sequence[str | dt.date | np.datetime64] | None = None,
        busdaycal: np.busdaycalendar | None = None,
    ) -> None:
        self._bushours_dict = _normalize_bushours(bushours)
        self._weights = _total_durations(self._bushours_dict)
        busday_kwargs: dict = {}
        if busdaycal is not None:
            busday_kwargs["busdaycal"] = busdaycal
        else:
            if weekmask is None:
                # Dict form: derive weekmask from which days have active intervals.
                # Uniform form: default to Mon–Fri.
                if isinstance(bushours, dict):
                    weekmask = "".join(
                        "1" if self._bushours_dict[i] else "0" for i in range(7)
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

    def get_transform(self) -> BusdayTransform:
        return BusdayTransform(
            self._bushours_dict,
            self._calendar_days,
            self._calendar_cumulative,
            self._weights,
            **self._busday_kwargs,
        )

    def set_default_locators_and_formatters(self, axis: Axis) -> None:
        class _AxisBusdayState(Protocol):
            _busday_kwargs: dict[str, object]
            _bushours: dict[int, list[tuple[float, float]]]

        axis_state = cast(_AxisBusdayState, axis)
        axis_state._busday_kwargs = self._busday_kwargs.copy()
        axis_state._bushours = self._bushours_dict.copy()

        if not isinstance(axis.get_major_locator(), BusdayLocator):
            majloc = AutoDateLocator()
            majloc.set_axis(axis)
            axis.set_major_locator(majloc)

        if not isinstance(axis.get_major_formatter(), mdates.DateFormatter):
            current_locator = axis.get_major_locator()
            if isinstance(current_locator, BusdayLocator):
                majfmt = mdates.AutoDateFormatter(current_locator.base_locator)
            else:
                majfmt = mdates.AutoDateFormatter(current_locator)
            axis.set_major_formatter(majfmt)

    def limit_range_for_scale(
        self, vmin: float, vmax: float, minpos: float
    ) -> tuple[float, float]:
        return vmin, vmax


def register_scale() -> None:
    """Register the ``"busday"`` scale with Matplotlib.

    Called automatically on ``import busdayaxis``, so explicit calls are
    not required. The function is idempotent — calling it again has no effect
    and existing code that calls it explicitly continues to work.

    After registration, ``ax.set_xscale("busday", ...)`` is available for the
    lifetime of the Python session. The keyword arguments ``bushours``,
    ``weekmask``, ``holidays``, and ``busdaycal`` are forwarded directly to
    [`busdayaxis.BusdayScale`](https://saemeon.github.io/busdayaxis/api/#busdayaxis.BusdayScale);
    ``axis`` is injected by Matplotlib automatically and cannot be passed.

    Examples
    --------

    ```python
    import busdayaxis          # scale is registered automatically
    import matplotlib.pyplot as plt
    import pandas as pd

    dates = pd.date_range("2025-01-01", periods=10, freq="D")
    values = range(10)

    fig, ax = plt.subplots()
    ax.plot(dates, values)
    ax.set_xscale("busday", bushours=(9, 17))  # kwargs forwarded to BusdayScale
    plt.show()
    ```
    """
    mscale.register_scale(BusdayScale)
