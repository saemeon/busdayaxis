"""Property tests across many scale configurations.

The forward transform is checked against an independent reference built on
``numpy.busday_count``; round-trips, tick placement and gap positions are
checked against the definition of the configured business schedule.
"""

import datetime as dt

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

import busdayaxis
from busdayaxis._scale import _normalize_bushours

HOLIDAYS = ["2025-01-01", "2025-01-20", "2025-02-17", "2025-04-18", "2025-12-25"]

CONFIGS = {
    "default": {},
    "9-17": {"bushours": (9, 17)},
    "9.5-16": {"bushours": (9.5, 16)},
    "lunch": {"bushours": [(9, 12), (13, 17)]},
    "per-day": {"bushours": {"Mon": [(9, 12), (13, 17)], "Fri": (9, 13)}},
    "fx": {"bushours": {"Sun": (22, 24), "Fri": (0, 22)}},
    "sunday": {"bushours": {"Sun": (10, 18)}},
    "strings": {"bushours": ("09:00", "17:30")},
    "time-objects": {"bushours": (dt.time(8, 15), dt.time(16, 45))},
    "mideast": {"weekmask": "Sun Mon Tue Wed Thu", "holidays": HOLIDAYS},
    "holidays": {"bushours": (9, 17), "holidays": HOLIDAYS},
    "busdaycal": {
        "bushours": (9, 17),
        "busdaycal": np.busdaycalendar(weekmask="1111100", holidays=HOLIDAYS),
    },
    "all-week": {"bushours": (9, 17), "weekmask": "1111111"},
}

params = pytest.mark.parametrize("kw", CONFIGS.values(), ids=CONFIGS.keys())


def _calendar(scale):
    """Return (weekmask bool[7], holidays datetime64[D]) the scale is using."""
    kw = scale._busday_kwargs
    cal = kw.get("busdaycal") or np.busdaycalendar(
        weekmask=kw.get("weekmask", "1111100"), holidays=kw.get("holidays", [])
    )
    return np.asarray(cal.weekmask, dtype=bool), cal.holidays


def _reference_busday_float(dates, scale):
    """Independent implementation of the documented mapping:
    weighted business days since 1970-01-01 + active time elapsed today."""
    bushours = scale._bushours_dict
    weekmask, holidays = _calendar(scale)
    days = dates.values.astype("datetime64[D]")
    hours = (dates - dates.normalize()).total_seconds().to_numpy() / 3600
    weekday = dates.weekday.to_numpy()

    epoch = np.datetime64("1970-01-01")
    # Days in [epoch, day) count positive, days in [day, epoch) negative.
    # (np.busday_count with begin > end counts (end, begin], so never reverse.)
    first, last = np.minimum(days, epoch), np.maximum(days, epoch)
    sign = np.where(days >= epoch, 1, -1)

    total = np.zeros(len(dates))
    for wd in range(7):
        if not weekmask[wd]:
            continue
        weight = sum(e - s for s, e in bushours[wd]) / 24
        only_wd = [i == wd for i in range(7)]
        count = np.busday_count(first, last, weekmask=only_wd, holidays=holidays)
        total += weight * sign * count

    is_busday = np.is_busday(days, weekmask=weekmask, holidays=holidays)
    for i in np.nonzero(is_busday)[0]:
        total[i] += (
            sum(np.clip(hours[i] - s, 0, e - s) for s, e in bushours[weekday[i]]) / 24
        )
    return total


def _random_dates(n, seed=0):
    rng = np.random.default_rng(seed)
    lo = pd.Timestamp("1900-01-01").value // 1000
    hi = pd.Timestamp("2200-01-01").value // 1000
    return pd.DatetimeIndex(pd.to_datetime(rng.integers(lo, hi, n), unit="us"))


@params
def test_forward_transform_matches_reference(kw):
    scale = busdayaxis.BusdayScale(**kw)
    dates = _random_dates(500).append(
        pd.date_range("2024-12-23", "2025-01-27", freq="15min")
    )
    got = scale.get_transform().transform(mdates.date2num(dates))
    # The scale accumulates fractional day weights over ~213k calendar days,
    # so float rounding reaches ~1e-7 days (~10 ms) far from 1970. 1e-6 days
    # (~0.09 s) is invisible on any plot but still catches 1 s truncation.
    np.testing.assert_allclose(
        got, _reference_busday_float(dates, scale), rtol=0, atol=1e-6
    )


@params
def test_round_trip_inside_sessions(kw):
    """Any instant strictly inside a session survives forward + inverse."""
    scale = busdayaxis.BusdayScale(**kw)
    bushours = _normalize_bushours(kw.get("bushours", (0, 24)))
    weekmask, holidays = _calendar(scale)

    rng = np.random.default_rng(1)
    days = pd.date_range("1950-01-01", "2150-01-01", freq="D")
    days = days[
        np.is_busday(
            days.values.astype("datetime64[D]"), weekmask=weekmask, holidays=holidays
        )
    ]
    days = days[[bool(bushours[d.weekday()]) for d in days]]
    picked = days[rng.integers(0, len(days), 500)]

    stamps = []
    for day in picked:
        s, e = bushours[day.weekday()][rng.integers(len(bushours[day.weekday()]))]
        stamps.append(day + pd.Timedelta(hours=s + (e - s) * rng.uniform(0, 0.999)))
    x = mdates.date2num(pd.DatetimeIndex(stamps).round("us"))

    t = scale.get_transform()
    back = t.inverted().transform(t.transform(x))
    assert np.max(np.abs(back - x)) * 86_400e6 < 2  # microseconds


LOCATORS = {
    "auto": lambda: busdayaxis.AutoDateLocator(),
    "day": lambda: busdayaxis.DayLocator(),
    "weekday": lambda: busdayaxis.WeekdayLocator(byweekday=mdates.MO),
    "hour": lambda: busdayaxis.HourLocator(byhour=range(0, 24, 2)),
    "minute": lambda: busdayaxis.MinuteLocator(byminute=[0, 30]),
}


@params
@pytest.mark.parametrize("make_locator", LOCATORS.values(), ids=LOCATORS.keys())
def test_ticks_only_on_business_time(kw, make_locator):
    dates = pd.date_range("2025-01-03", "2025-01-14", freq="h")
    fig, ax = plt.subplots()
    ax.plot(dates, np.arange(len(dates)))
    ax.set_xscale("busday", **kw)
    ax.xaxis.set_major_locator(make_locator())
    fig.canvas.draw()
    ticks = pd.to_datetime(mdates.num2date(ax.get_xticks(), tz="UTC")).tz_localize(None)
    plt.close(fig)

    scale = busdayaxis.BusdayScale(**kw)
    weekmask, holidays = _calendar(scale)
    bushours = scale._bushours_dict
    assert len(ticks) > 0
    for tick in ticks:
        assert np.is_busday(
            np.datetime64(tick.date()), weekmask=weekmask, holidays=holidays
        ), tick
        hour = (tick - tick.normalize()).total_seconds() / 3600
        midnight = hour == 0  # day-level locators keep midnight ticks by design
        assert midnight or any(s <= hour < e for s, e in bushours[tick.weekday()]), tick


@params
def test_gaps_are_at_session_closes(kw):
    dates = pd.date_range("2025-01-03", "2025-01-14", freq="h")
    fig, ax = plt.subplots()
    ax.plot(dates, np.arange(len(dates)))
    ax.set_xscale("busday", **kw)
    gaps = [a.get_xdata()[0] for a in busdayaxis.mark_gaps(ax)]
    plt.close(fig)

    bushours = busdayaxis.BusdayScale(**kw)._bushours_dict
    for g in pd.to_datetime(mdates.num2date(gaps, tz="UTC")).tz_localize(None):
        hour = (g - g.normalize()).total_seconds() / 3600
        closes = {e for _, e in bushours[g.weekday()]}
        # a close at 24:00 is reported as the next day's 00:00
        prev_closes = {e - 24 for _, e in bushours[(g.weekday() - 1) % 7]}
        assert min(abs(hour - c) for c in closes | prev_closes) < 1e-6, g
