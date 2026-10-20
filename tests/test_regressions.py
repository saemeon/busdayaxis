"""Regression tests for bugs fixed in 0.2.2."""

import datetime as dt

import matplotlib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

import busdayaxis


def _weekdays(ticks):
    return {mdates.num2date(t, tz="UTC").strftime("%a") for t in ticks}


def _hhmm(ticks):
    return [mdates.num2date(t, tz="UTC").strftime("%H:%M") for t in ticks]


# ── rcParams["timezone"] must not shift the naive wall-clock axis ─────────────


@pytest.mark.parametrize("tz", ["UTC", "America/New_York", "Asia/Tokyo"])
def test_rcparams_timezone_does_not_shift_scale(tz):
    x = mdates.date2num([dt.datetime(2025, 1, 6, 9, 30), dt.datetime(2025, 1, 6, 15)])
    with matplotlib.rc_context({"timezone": tz}):
        fig, ax = plt.subplots()
        ax.set_xscale("busday", bushours=(9.5, 16))
        y = ax.xaxis.get_transform().transform(x)
        back = ax.xaxis.get_transform().inverted().transform(y)
        plt.close(fig)
    assert y[1] - y[0] == pytest.approx(5.5 / 24)
    np.testing.assert_allclose(back, x)


def test_rcparams_timezone_does_not_shift_locators_or_gaps():
    dates = pd.date_range("2025-01-06 09:30", "2025-01-08 16:00", freq="30min")
    with matplotlib.rc_context({"timezone": "America/New_York"}):
        fig, ax = plt.subplots()
        ax.plot(dates, range(len(dates)))
        ax.set_xscale("busday", bushours=(9.5, 16))

        ax.xaxis.set_major_locator(busdayaxis.HourLocator(byhour=[10, 12, 14]))
        fig.canvas.draw()
        assert set(_hhmm(ax.get_xticks())) == {"10:00", "12:00", "14:00"}

        mid = busdayaxis.MidBusdayLocator()
        mid.set_axis(ax.xaxis)
        assert set(_hhmm(mid())) == {"12:45"}

        gaps = busdayaxis.mark_gaps(ax)
        assert {_hhmm([g.get_xdata()[0]])[0] for g in gaps} == {"16:00"}

        labels = [t.get_text() for t in ax.get_xticklabels()]
        plt.close(fig)
    assert "01-06 10" in labels  # labelled in wall-clock time, not New York


# ── set_xscale before plotting keeps the busday locator ───────────────────────


def test_set_xscale_before_plot_keeps_busday_locator():
    dates = pd.date_range("2025-01-01", periods=30)  # includes weekends
    fig, ax = plt.subplots()
    ax.set_xscale("busday")
    ax.plot(dates, range(30))
    fig.canvas.draw()

    assert isinstance(ax.xaxis.get_major_locator(), busdayaxis.BusdayLocator)
    assert _weekdays(ax.get_xticks()).isdisjoint({"Sat", "Sun"})
    plt.close(fig)


def test_set_xscale_before_plot_matches_plot_before_set_xscale():
    dates = pd.date_range("2025-01-03", periods=6)

    fig1, ax1 = plt.subplots()
    ax1.plot(dates, range(6))
    ax1.set_xscale("busday")
    fig1.canvas.draw()

    fig2, ax2 = plt.subplots()
    ax2.set_xscale("busday")
    ax2.plot(dates, range(6))
    fig2.canvas.draw()

    np.testing.assert_allclose(ax1.get_xticks(), ax2.get_xticks())
    plt.close(fig1)
    plt.close(fig2)


# ── NaN / NaT / out-of-range values ───────────────────────────────────────────


def test_nat_in_x_data_draws():
    x = pd.to_datetime(["2025-01-06 10:00", None, "2025-01-08 10:00"])
    fig, ax = plt.subplots()
    ax.plot(x, [1, 2, 3])
    ax.set_xscale("busday", bushours=(9, 17))
    fig.canvas.draw()
    plt.close(fig)


def test_transform_passes_nan_through_both_ways():
    scale = busdayaxis.BusdayScale(bushours=(9, 17))
    fwd = scale.get_transform()
    x = mdates.date2num(dt.datetime(2025, 1, 6, 10))
    y = fwd.transform(np.array([np.nan, x, np.inf]))
    assert np.isnan(y[0]) and np.isnan(y[2]) and np.isfinite(y[1])

    back = fwd.inverted().transform(np.array([np.nan, y[1]]))
    assert np.isnan(back[0])
    assert back[1] == pytest.approx(x)


@pytest.mark.parametrize("year", [1600, 2300])
def test_dates_outside_calendar_map_to_nan(year):
    scale = busdayaxis.BusdayScale()
    x = mdates.date2num(dt.datetime(year, 1, 3, 10))
    assert np.isnan(scale.get_transform().transform(np.array([x]))[0])


# ── holidays= accepts pandas / datetime64 input ───────────────────────────────


@pytest.mark.parametrize(
    "holidays",
    [
        ["2025-01-07"],
        [dt.date(2025, 1, 7)],
        [pd.Timestamp("2025-01-07")],
        pd.DatetimeIndex(["2025-01-07"]),
        np.array(["2025-01-07"], dtype="datetime64[ns]"),
        pd.Series(pd.to_datetime(["2025-01-07"])),
    ],
)
def test_holidays_accepts_pandas_and_datetime64(holidays):
    scale = busdayaxis.BusdayScale(holidays=holidays)
    t = scale.get_transform()
    mon, wed = mdates.date2num([dt.datetime(2025, 1, 6), dt.datetime(2025, 1, 8)])
    a, b = t.transform(np.array([mon, wed]))
    assert b - a == pytest.approx(1.0)  # Tue 2025-01-07 collapsed


# ── locator wrappers forward positional arguments ─────────────────────────────


def test_locator_wrappers_forward_positional_args():
    hour = busdayaxis.HourLocator([9, 12])
    assert hour._keep_midnight_ticks is None
    assert hour.base_locator.rule._rrule._byhour == (9, 12)

    wk = busdayaxis.WeekdayLocator(mdates.MO)
    assert wk._keep_midnight_ticks is None
    assert wk.base_locator.rule._rrule._byweekday == (0,)

    day = busdayaxis.DayLocator(keep_midnight_ticks=False, interval=2)
    assert day._keep_midnight_ticks is False


def test_keep_midnight_ticks_positional_is_deprecated_but_works():
    # v0.2.1 call forms keep working, with a deprecation warning.
    with pytest.warns(DeprecationWarning, match="keep_midnight_ticks=True"):
        loc = busdayaxis.BusdayLocator(mdates.DayLocator(), True)
    assert loc._keep_midnight_ticks is True

    with pytest.warns(DeprecationWarning, match="keep_midnight_ticks=False"):
        hour = busdayaxis.HourLocator(False, byhour=[9, 12])
    assert hour._keep_midnight_ticks is False
    assert hour.base_locator.rule._rrule._byhour == (9, 12)


def test_keep_midnight_ticks_positional_and_keyword_raises():
    with pytest.raises(TypeError):
        busdayaxis.BusdayLocator(mdates.DayLocator(), True, keep_midnight_ticks=True)
    with pytest.raises(TypeError):
        busdayaxis.HourLocator(True, keep_midnight_ticks=True)


# ── sub-second precision ──────────────────────────────────────────────────────


def test_forward_transform_keeps_subsecond_precision():
    t = busdayaxis.BusdayScale(bushours=(9, 17)).get_transform()
    dates = pd.date_range("2025-01-06 10:00", periods=5, freq="250ms")
    diffs_s = np.diff(t.transform(mdates.date2num(dates))) * 86400
    np.testing.assert_allclose(diffs_s, 0.25, rtol=1e-6)


@pytest.mark.parametrize(
    "stamp",
    ["2025-01-06 12:30:00", "2025-01-06 16:59:59", "2025-01-10 13:17:41.250"],
)
def test_round_trip_is_exact(stamp):
    t = busdayaxis.BusdayScale(bushours=(9, 17)).get_transform()
    x = mdates.date2num(pd.Timestamp(stamp))
    back = t.inverted().transform(t.transform(np.array([x])))[0]
    assert abs(back - x) * 86400e6 < 1  # within a microsecond


def test_microsecond_locator_ticks_are_distinct():
    dates = pd.date_range("2025-01-06 10:00:00", periods=11, freq="100ms")
    fig, ax = plt.subplots()
    ax.plot(dates, range(11))
    ax.set_xscale("busday", bushours=(9, 17))
    ax.xaxis.set_major_locator(busdayaxis.MicrosecondLocator(interval=250_000))
    fig.canvas.draw()
    ticks = ax.get_xticks()
    pixels = ax.transData.transform(np.column_stack([ticks, np.zeros_like(ticks)]))
    assert len(np.unique(np.round(pixels[:, 0], 3))) == len(ticks) > 1
    plt.close(fig)
