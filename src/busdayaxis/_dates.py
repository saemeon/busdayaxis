# Copyright (c) Simon Niederberger.
# Distributed under the terms of the MIT License.

"""Vectorized conversion between Matplotlib date numbers and naive datetime64.

busdayaxis treats all datetimes as naive wall-clock time. Matplotlib stores
naive datetimes as if they were UTC, so the conversion back must also be done
in UTC, never in ``rcParams["timezone"]`` (which ``mdates.num2date`` applies).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib.dates as mdates
import numpy as np

if TYPE_CHECKING:
    from numpy.typing import ArrayLike, NDArray

US_PER_DAY = 86_400_000_000

# Date numbers beyond this many days from the epoch would overflow int64
# microseconds; they are far outside any representable calendar anyway.
_MAX_ABS_DAYS = 1e8


def _epoch_us() -> np.datetime64:
    return np.datetime64(mdates.get_epoch(), "us")


def num_to_datetime64(values: ArrayLike) -> NDArray[np.datetime64]:
    """Matplotlib date numbers -> naive ``datetime64[us]``.

    Non-finite (and absurdly large) values become ``NaT``.
    """
    x = np.asarray(values, dtype=float)
    valid = np.isfinite(x) & (np.abs(x) < _MAX_ABS_DAYS)
    us = np.zeros(x.shape, dtype=np.int64)
    us[valid] = np.round(x[valid] * US_PER_DAY)
    out = _epoch_us() + us.astype("timedelta64[us]")
    out[~valid] = np.datetime64("NaT", "us")
    return out


def datetime64_to_num(values: ArrayLike) -> NDArray[np.float64]:
    """Naive datetime64 -> Matplotlib date numbers (``NaT`` -> ``nan``)."""
    d = np.asarray(values, dtype="datetime64[us]")
    out = (d - _epoch_us()).astype(np.int64) / US_PER_DAY
    return np.where(np.isnat(d), np.nan, out)


def intraday_fraction(values: NDArray[np.datetime64]) -> NDArray[np.float64]:
    """Fraction of the day elapsed since midnight, at microsecond resolution."""
    us = values.astype("datetime64[us]")
    return (us - us.astype("datetime64[D]")).astype(np.int64) / US_PER_DAY
