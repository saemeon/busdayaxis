# Copyright (c) Simon Niederberger.
# Distributed under the terms of the Modified BSD License.

from __future__ import annotations

from typing import Any

import matplotlib.dates as mdates
import matplotlib.scale as mscale
import matplotlib.transforms as mtransforms
import numpy as np
from matplotlib.axis import Axis

from busdayaxis._locator import AutoDateLocator, BusdayLocator

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
WEEKDAYS_MAP = {name: i for i, name in enumerate(WEEKDAYS)}

#####################################################################
# Helper functions
#####################################################################


def _validate_hours(start: float, end: float, label: str = "hours") -> None:
    if not (0 <= start <= end <= 24):
        raise ValueError(f"{label} must satisfy 0 <= start <= end <= 24")


_BushoursInput = (
    tuple[float, float]
    | list[tuple[float, float]]
    | dict[str | int, tuple[float, float]]
)


def _normalize_bushours(bushours: _BushoursInput) -> dict[int, tuple[float, float]]:
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


def _bushours_bounds(
    bushours_dict: dict[int, tuple[float, float]],
) -> tuple[np.ndarray, np.ndarray]:
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


def _build_weighted_calendar(
    weights: np.ndarray, **busday_kwargs: Any
) -> tuple[np.ndarray, np.ndarray]:
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
    values: Any,
    bushours_dict: dict[int, tuple[float, float]],
    calendar_days: np.ndarray,
    cumulative: np.ndarray,
    weights: np.ndarray,
    **busday_kwargs: Any,
) -> np.ndarray:
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
    values: Any,
    bushours_dict: dict[int, tuple[float, float]],
    calendar_days: np.ndarray,
    cumulative: np.ndarray,
    weights: np.ndarray,
) -> np.ndarray:
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
        self,
        bushours_dict: dict[int, tuple[float, float]],
        calendar_days: np.ndarray,
        cumulative: np.ndarray,
        weights: np.ndarray,
        **busday_kwargs: Any,
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
        Active hours per weekday (hours as floats, 0–24).

        Three forms:

        - ``(start, end)``:
            Same session for all days (e.g. ``(9, 17)``). The weekmask still
            applies, so off-days (Sat/Sun by default) are collapsed regardless.
            Default ``(0, 24)``.

            Example:

            ```python
            bushours=(9, 17)  # 9 AM to 5 PM every day, excluding weekends
            ```

            To apply also on weekends, use:

            ```python
            bushours=(9, 17), weekmask="1111111"  # Mon–Sun
            ```

        - list of 7 ``(start, end)`` tuples:
            One tuple per weekday Monday–Sunday, fully explicit.

            Example:

            ```python
            bushours=[
                (9, 17),  # Mon
                (9, 17),  # Tue
                (9, 17),  # Wed
                (9, 17),  # Thu
                (9, 17),  # Fri
                (0, 0),   # Sat
                (0, 0),   # Sun
            ]
            ```

        - dict ``{weekday: (start, end)}``:
            Per-day overrides; keys are integers 0–6 or names
            ``"Mon"``–``"Sun"``. Defaults for unspecified days:

            | Day  | Key  | Default |
            |------|------|---------|
            | Mon  | 0    | `(0, 24)` |
            | Tue  | 1    | `(0, 24)` |
            | Wed  | 2    | `(0, 24)` |
            | Thu  | 3    | `(0, 24)` |
            | Fri  | 4    | `(0, 24)` |
            | Sat  | 5    | `(0, 0)`  |
            | Sun  | 6    | `(0, 0)`  |

            The weekmask is derived automatically: days with non-zero hours
            are treated as business days, so passing ``{"Sun": (10, 18)}``
            will show Sundays without a separate *weekmask* override.

            Example:

            ```python
            bushours={"Sun": (10, 18)}  # Show Sundays with custom hours, Weekdays 00-24
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

        - For dict / list-of-7 *bushours*: derived automatically — days with
          non-zero hours become business days.
        - For uniform ``(start, end)`` *bushours*: ``"1111100"`` (Mon–Fri).

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

        ```python
        cal = np.busdaycalendar(weekmask="Mon Tue Wed Thu Fri",
                                holidays=["2025-01-01"])
        ax.set_xscale("busday", busdaycal=cal)
        ```

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

    Per-day hours — Friday early close at 16:00, weekends closed:

    ```python
    ax.set_xscale("busday", bushours={"Mon": (9, 17), "Fri": (9, 16)})
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
        bushours: _BushoursInput = (0, 24),
        weekmask: str | None = None,
        holidays: list[str] | None = None,
        busdaycal: np.busdaycalendar | None = None,
    ) -> None:
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

    def get_transform(self) -> BusdayTransform:
        return BusdayTransform(
            self._bushours_dict,
            self._calendar_days,
            self._calendar_cumulative,
            self._weights,
            **self._busday_kwargs,
        )

    def set_default_locators_and_formatters(self, axis: Axis) -> None:
        axis._busday_kwargs = self._busday_kwargs.copy()
        axis._bushours = self._bushours_dict.copy()

        if not isinstance(axis.get_major_locator(), BusdayLocator):
            majloc = AutoDateLocator()
            majloc.set_axis(axis)
            axis.set_major_locator(majloc)

        if not isinstance(axis.get_major_formatter(), mdates.DateFormatter):
            majfmt = mdates.AutoDateFormatter(axis.get_major_locator().base_locator)
            axis.set_major_formatter(majfmt)

    def limit_range_for_scale(
        self, vmin: float, vmax: float, minpos: float
    ) -> tuple[float, float]:
        return vmin, vmax


def register_scale() -> None:
    """Register the ``"busday"`` scale with Matplotlib.

    Call once at the start of your script before using
    ``ax.set_xscale("busday")``.

    Examples
    --------

    ```python
    import busdayaxis
    import matplotlib.pyplot as plt
    import pandas as pd

    busdayaxis.register_scale()

    dates = pd.date_range("2025-01-01", periods=10, freq="D")
    values = range(10)

    fig, ax = plt.subplots()
    ax.plot(dates, values)
    ax.set_xscale("busday", bushours=(9, 17))
    plt.show()
    ```
    """
    mscale.register_scale(BusdayScale)
