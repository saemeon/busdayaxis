import datetime as dt

import pytest  # noqa

from busdayaxis._scale import (
    _build_weighted_calendar,
    _busday_float_to_datetime,
    _coerce_intervals,
    _datetime_to_busday_float,
    _normalize_bushours,
    _to_hour_float,
    _total_durations,
)


def _fwd(bushours, dates, weekmask="1111100"):
    """Forward transform helper: datetimes → busday floats."""
    d = _normalize_bushours(bushours)
    w = _total_durations(d)
    cal, cum = _build_weighted_calendar(w, weekmask=weekmask)
    kw = {"weekmask": weekmask}
    return _datetime_to_busday_float(dates, d, cal, cum, w, **kw)


def _inv(bushours, values, weekmask="1111100"):
    """Inverse transform helper: busday floats → datetimes."""
    d = _normalize_bushours(bushours)
    w = _total_durations(d)
    cal, cum = _build_weighted_calendar(w, weekmask=weekmask)
    return _busday_float_to_datetime(values, d, cal, cum, w)


def test_to_hour_float_int():
    assert _to_hour_float(9) == 9.0


def test_to_hour_float_float():
    assert _to_hour_float(9.5) == 9.5


def test_to_hour_float_string_hhmm():
    assert _to_hour_float("09:30") == 9.5


def test_to_hour_float_string_hhmmss():
    assert _to_hour_float("09:30:30") == pytest.approx(9.5 + 30 / 3600)


def test_to_hour_float_time_object():
    assert _to_hour_float(dt.time(9, 30)) == 9.5


def test_to_hour_float_time_microseconds():
    t = dt.time(9, 30, 0, 500_000)
    assert _to_hour_float(t) == pytest.approx(9.5 + 500_000 / 3_600_000_000)


def test_to_hour_float_invalid_string():
    with pytest.raises(ValueError):
        _to_hour_float("not-a-time")


def test_coerce_intervals_single_tuple():
    assert _coerce_intervals((9, 17)) == [(9.0, 17.0)]


def test_coerce_intervals_strings():
    assert _coerce_intervals(("09:00", "17:00")) == [(9.0, 17.0)]


def test_coerce_intervals_time_objects():
    assert _coerce_intervals((dt.time(9), dt.time(17))) == [(9.0, 17.0)]


def test_coerce_intervals_mixed():
    assert _coerce_intervals((9, "17:30")) == [(9.0, 17.5)]


def test_coerce_intervals_invalid_order():
    with pytest.raises(ValueError):
        _coerce_intervals((17, 9))


def test_coerce_intervals_out_of_range():
    with pytest.raises(ValueError):
        _coerce_intervals((0, 25))


def test_coerce_intervals_list_of_two():
    assert _coerce_intervals([(9, 12), (13, 17)]) == [(9.0, 12.0), (13.0, 17.0)]


def test_coerce_intervals_overlap():
    with pytest.raises(ValueError):
        _coerce_intervals([(9, 13), (12, 17)])


def test_coerce_intervals_invalid_input():
    with pytest.raises(ValueError):
        _coerce_intervals((9, 17, 5))  # type: ignore[arg-type]


def test_normalize_bushours_int_key():
    from busdayaxis._scale import _normalize_bushours

    result = _normalize_bushours({0: (9, 17), 4: (9, 13)})
    assert result[0] == [(9.0, 17.0)]
    assert result[4] == [(9.0, 13.0)]


def test_normalize_bushours_multi_interval():
    from busdayaxis._scale import _normalize_bushours

    result = _normalize_bushours({0: [(9, 12), (13, 17)]})
    assert result[0] == [(9.0, 12.0), (13.0, 17.0)]


def test_normalize_bushours_uniform_list():
    from busdayaxis._scale import _normalize_bushours

    result = _normalize_bushours([(9, 12), (13, 17)])
    assert result[0] == [(9.0, 12.0), (13.0, 17.0)]
    assert result[3] == [(9.0, 12.0), (13.0, 17.0)]


def test_normalize_bushours_invalid_key():
    from busdayaxis._scale import _normalize_bushours

    with pytest.raises(ValueError):
        _normalize_bushours({"Funday": (9, 17)})  # type: ignore[arg-type]


def test_normalize_bushours_invalid_input():
    from busdayaxis._scale import _normalize_bushours

    with pytest.raises(ValueError):
        _normalize_bushours((9, 17, 5))  # type: ignore[arg-type]


# ── _coerce_intervals additional ─────────────────────────────────────────────


# Intervals passed out of order are sorted automatically.
def test_coerce_intervals_sorted():
    result = _coerce_intervals([(13, 17), (9, 12)])
    assert result == [(9.0, 12.0), (13.0, 17.0)]


# ── _total_durations ──────────────────────────────────────────────────────────


def test_total_durations_single_interval():
    d = _normalize_bushours((9, 17))
    w = _total_durations(d)
    assert w == pytest.approx([8 / 24] * 7)


def test_total_durations_multi_interval():
    d = _normalize_bushours([(9, 12), (13, 17)])
    w = _total_durations(d)
    assert w == pytest.approx([7 / 24] * 7)


def test_total_durations_per_day_dict():
    # Mon: 8h, all others default to 24h, weekends 0h
    d = _normalize_bushours({"Mon": (9, 17)})
    w = _total_durations(d)
    assert w[0] == pytest.approx(8 / 24)  # Mon
    assert w[1] == pytest.approx(24 / 24)  # Tue (default full day)
    assert w[5] == pytest.approx(0.0)  # Sat (default closed)


# ── Calculation tests (epoch = 1970-01-01, Thursday) ─────────────────────────


# With bushours=(0, 24), weight = 1 day per business day.
# Thu=0, Fri=1, weekend skipped → Mon=2.
def test_forward_weekend_skipped():
    result = _fwd((0, 24), ["1970-01-01", "1970-01-02", "1970-01-05"])
    assert result == pytest.approx([0.0, 1.0, 2.0])


# With bushours=(9, 17), weight = 8/24 per day.
# 09:00 is the session open → busday 0.0. Midday 13:00 is 4h in → 4/24.
# Session close 17:00 → 8/24. Overnight gap: Fri 09:00 equals Thu 17:00.
def test_forward_single_interval_intraday():
    dates = [
        dt.datetime(1970, 1, 1, 9),  # Thu 09:00 — session open
        dt.datetime(1970, 1, 1, 13),  # Thu 13:00 — 4h into session
        dt.datetime(1970, 1, 1, 17),  # Thu 17:00 — session close
        dt.datetime(1970, 1, 2, 9),  # Fri 09:00 — overnight gap collapsed
    ]
    result = _fwd((9, 17), dates)
    assert result == pytest.approx([0.0, 4 / 24, 8 / 24, 8 / 24])


# Pre-market time clips to session open (same position as 09:00).
def test_forward_pre_market_clips_to_open():
    dates = [dt.datetime(1970, 1, 1, 7), dt.datetime(1970, 1, 1, 9)]
    result = _fwd((9, 17), dates)
    assert result[0] == pytest.approx(result[1])


# With bushours=[(9,12),(13,17)], weight = 7/24 per day.
# Lunch gap (12:00–13:00) collapses: 12:00, 12:30, and 13:00 all map to 3/24.
# Afternoon 15:00 is 2h into the second interval → 3/24 + 2/24 = 5/24.
def test_forward_multi_interval_lunch_collapses():
    dates = [
        dt.datetime(1970, 1, 1, 9),  # session open
        dt.datetime(1970, 1, 1, 12),  # end of morning
        dt.datetime(1970, 1, 1, 12, 30),  # lunch gap
        dt.datetime(1970, 1, 1, 13),  # afternoon open
        dt.datetime(1970, 1, 1, 15),  # 2h into afternoon
        dt.datetime(1970, 1, 1, 17),  # session close
        dt.datetime(1970, 1, 2, 9),  # Fri open — overnight gap collapsed
    ]
    result = _fwd([(9, 12), (13, 17)], dates)
    assert result == pytest.approx(
        [0.0, 3 / 24, 3 / 24, 3 / 24, 5 / 24, 7 / 24, 7 / 24]
    )


# Inverse of a forward transform returns the original datetime (within sessions).
def test_inverse_roundtrip_single_interval():
    dates = [
        dt.datetime(1970, 1, 1, 10),
        dt.datetime(1970, 1, 1, 14),
        dt.datetime(1970, 1, 2, 11),
    ]
    fwd = _fwd((9, 17), dates)
    inv = _inv((9, 17), fwd).astype("datetime64[s]").astype(object)
    for orig, recovered in zip(dates, inv):
        assert recovered == orig


# Inverse of a forward transform with multiple intervals roundtrips correctly.
def test_inverse_roundtrip_multi_interval():
    dates = [
        dt.datetime(1970, 1, 1, 10),  # morning
        dt.datetime(1970, 1, 1, 15),  # afternoon
        dt.datetime(1970, 1, 2, 11),  # next day morning
    ]
    fwd = _fwd([(9, 12), (13, 17)], dates)
    inv = _inv([(9, 12), (13, 17)], fwd).astype("datetime64[s]").astype(object)
    for orig, recovered in zip(dates, inv):
        assert recovered == orig


# Inverse at busday 0.0 returns the session open (09:00 with bushours=(9,17)).
def test_inverse_at_zero_returns_session_open():
    inv = _inv((9, 17), [0.0]).astype("datetime64[s]").astype(object)
    assert inv[0] == dt.datetime(1970, 1, 1, 9)


# Post-market time clips to session close (symmetric to the pre-market test).
def test_forward_post_market_clips_to_close():
    dates = [dt.datetime(1970, 1, 1, 17), dt.datetime(1970, 1, 1, 20)]
    result = _fwd((9, 17), dates)
    assert result[0] == pytest.approx(result[1])


# Sat and Sun both collapse to the same value as Fri close (= Mon open).
def test_forward_weekend_collapses():
    fri_close = _fwd((9, 17), [dt.datetime(1970, 1, 2, 17)])  # Fri 17:00
    sat = _fwd((9, 17), [dt.datetime(1970, 1, 3, 12)])  # Sat (non-business)
    sun = _fwd((9, 17), [dt.datetime(1970, 1, 4, 12)])  # Sun (non-business)
    mon_open = _fwd((9, 17), [dt.datetime(1970, 1, 5, 9)])  # Mon 09:00
    assert fri_close == pytest.approx(sat)
    assert fri_close == pytest.approx(sun)
    assert fri_close == pytest.approx(mon_open)


# A holiday behaves like a weekend: it collapses to the preceding close.
def test_forward_holiday_collapses():
    d = _normalize_bushours((9, 17))
    w = _total_durations(d)
    cal, cum = _build_weighted_calendar(w, weekmask="1111100", holidays=["1970-01-02"])
    kw = {"weekmask": "1111100", "holidays": ["1970-01-02"]}
    thu_close = _datetime_to_busday_float(
        [dt.datetime(1970, 1, 1, 17)], d, cal, cum, w, **kw
    )
    fri_holiday = _datetime_to_busday_float(
        [dt.datetime(1970, 1, 2, 12)], d, cal, cum, w, **kw
    )
    assert thu_close == pytest.approx(fri_holiday)


def test_inverted_transform_roundtrip():
    """InvertedBusdayTransform.inverted() returns a BusdayTransform."""
    import matplotlib.pyplot as plt
    import pandas as pd

    import busdayaxis

    busdayaxis.register_scale()
    dates = pd.date_range("2025-01-06", periods=5, freq="D")
    fig, ax = plt.subplots()
    ax.plot(dates, range(5))
    ax.set_xscale("busday")

    transform = ax.xaxis._scale.get_transform()
    inv = transform.inverted()
    assert inv.inverted() is not None

    plt.close(fig)


def test_import():
    import busdayaxis

    assert hasattr(busdayaxis, "BusdayScale")
    assert hasattr(busdayaxis, "BusdayLocator")


def test_busday_scale_registration():
    import busdayaxis as busdayaxis

    busdayaxis.register_scale()


def test_busday_scale_with_holidays():
    import matplotlib.pyplot as plt

    holidays = ["2024-01-01", "2024-12-25"]

    fig, ax = plt.subplots()
    ax.set_xscale("busday", holidays=holidays)

    plt.close(fig)


def test_plot_dates():
    import matplotlib.pyplot as plt
    import pandas as pd

    dates = pd.date_range("2024-01-01", periods=10, freq="D")
    values = range(len(dates))

    fig, ax = plt.subplots()
    ax.plot(dates, values)
    ax.set_xscale("busday")

    plt.close(fig)


def test_per_day_bushours():
    """Per-day bushours with different hours per weekday."""
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    import pandas as pd

    import busdayaxis

    busdayaxis.register_scale()

    bushours = {
        "Mon": (9, 17),
        "Tue": (9, 17),
        "Wed": (9, 12),
        "Thu": (9, 22),
        "Fri": (9, 12),
    }

    dates = pd.date_range("2025-01-06", periods=5 * 8, freq="h")  # Mon-Fri
    values = range(len(dates))

    fig, ax = plt.subplots()
    ax.plot(dates, values)
    ax.set_xscale("busday", bushours=bushours)

    # Set locators before scale to avoid AutoDateLocator issues
    ax.xaxis.set_major_locator(busdayaxis.BusdayLocator(mdates.HourLocator()))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%a %H:%M"))

    plt.close(fig)


def test_bushours_tuple():
    """Simple tuple bushours (same hours every day)."""
    import matplotlib.pyplot as plt
    import pandas as pd

    dates = pd.date_range("2024-01-01", periods=10, freq="D")
    values = range(len(dates))

    fig, ax = plt.subplots()
    ax.plot(dates, values)
    ax.set_xscale("busday", bushours=(9, 17))

    plt.close(fig)


def test_bushours_multi_interval_uniform():
    """List of intervals applied uniformly (e.g. morning + afternoon sessions)."""
    import matplotlib.pyplot as plt
    import pandas as pd

    dates = pd.date_range("2025-01-06", periods=5 * 8, freq="h")
    fig, ax = plt.subplots()
    ax.plot(dates, range(len(dates)))
    ax.set_xscale("busday", bushours=[(9, 12), (13, 17)])
    plt.close(fig)


def test_bushours_multi_interval_per_day():
    """Per-day dict where some days have multiple intervals."""
    import matplotlib.pyplot as plt
    import pandas as pd

    dates = pd.date_range("2025-01-06", periods=5 * 8, freq="h")
    fig, ax = plt.subplots()
    ax.plot(dates, range(len(dates)))
    ax.set_xscale("busday", bushours={"Mon": [(9, 12), (13, 17)], "Fri": (9, 13)})
    plt.close(fig)


def test_custom_weekmask():
    """Custom weekmask (e.g., Sun-Thu for GCC markets)."""
    import matplotlib.pyplot as plt
    import pandas as pd

    dates = pd.date_range("2024-01-01", periods=14, freq="D")
    values = range(len(dates))

    fig, ax = plt.subplots()
    ax.plot(dates, values)
    ax.set_xscale("busday", weekmask="Sun Mon Tue Wed Thu")

    plt.close(fig)


def test_busdaycal_parameter():
    """busdaycal overrides weekmask and holidays."""
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd

    cal = np.busdaycalendar(weekmask="1111100", holidays=["2024-12-25"])
    dates = pd.date_range("2024-12-23", periods=7, freq="D")

    fig, ax = plt.subplots()
    ax.plot(dates, range(len(dates)))
    ax.set_xscale("busday", busdaycal=cal)

    plt.close(fig)


def test_bushours_string_tuple():
    """bushours accepts ISO time strings."""
    import matplotlib.pyplot as plt
    import pandas as pd

    dates = pd.date_range("2024-01-01", periods=10, freq="D")
    fig, ax = plt.subplots()
    ax.plot(dates, range(len(dates)))
    ax.set_xscale("busday", bushours=("09:00", "17:00"))
    plt.close(fig)


def test_bushours_time_object_tuple():
    """bushours accepts datetime.time objects."""
    import matplotlib.pyplot as plt
    import pandas as pd

    dates = pd.date_range("2024-01-01", periods=10, freq="D")
    fig, ax = plt.subplots()
    ax.plot(dates, range(len(dates)))
    ax.set_xscale("busday", bushours=(dt.time(9), dt.time(17)))
    plt.close(fig)


def test_bushours_dict_with_strings():
    """Per-day bushours dict accepts ISO time strings as values."""
    import matplotlib.pyplot as plt
    import pandas as pd

    dates = pd.date_range("2024-01-01", periods=10, freq="D")
    fig, ax = plt.subplots()
    ax.plot(dates, range(len(dates)))
    ax.set_xscale(
        "busday", bushours={"Mon": ("09:00", "17:00"), "Fri": ("09:00", "13:00")}
    )
    plt.close(fig)


def test_bushours_dict_with_time_objects():
    """Per-day bushours dict accepts datetime.time objects as values."""
    import matplotlib.pyplot as plt
    import pandas as pd

    dates = pd.date_range("2024-01-01", periods=10, freq="D")
    fig, ax = plt.subplots()
    ax.plot(dates, range(len(dates)))
    ax.set_xscale("busday", bushours={"Mon": (dt.time(9), dt.time(17))})
    plt.close(fig)


# ── _weekday_from_days ────────────────────────────────────────────────────────


def test_weekday_from_days_epoch():
    """1970-01-01 was a Thursday; verify the +3 trick for Mon=0 convention."""
    import numpy as np

    from busdayaxis._scale import _weekday_from_days

    days = np.array(
        ["1970-01-01", "1970-01-02", "1970-01-05", "1970-01-06"],
        dtype="datetime64[D]",
    )
    assert list(_weekday_from_days(days)) == [3, 4, 0, 1]  # Thu, Fri, Mon, Tue


# ── _coerce_intervals additional edge cases ───────────────────────────────────


def test_coerce_intervals_single_element_list():
    """A one-element list is accepted."""
    assert _coerce_intervals([(9, 17)]) == [(9.0, 17.0)]


def test_coerce_intervals_touching():
    """Intervals that share an endpoint are not overlapping and are accepted."""
    assert _coerce_intervals([(9, 12), (12, 17)]) == [(9.0, 12.0), (12.0, 17.0)]


# ── _normalize_bushours default fallbacks ────────────────────────────────────


def test_normalize_bushours_dict_defaults():
    """Unspecified Mon–Fri default to [(0, 24)]; Sat/Sun default to []."""
    result = _normalize_bushours({"Mon": (9, 17)})
    assert result[1] == [(0.0, 24.0)]  # Tue
    assert result[4] == [(0.0, 24.0)]  # Fri
    assert result[5] == []  # Sat
    assert result[6] == []  # Sun


# ── _total_durations: explicitly-closed day ───────────────────────────────────


def test_total_durations_empty_day():
    """A day with an empty interval list contributes weight 0."""
    d = _normalize_bushours({0: []})  # Mon explicitly closed, others default
    w = _total_durations(d)
    assert w[0] == pytest.approx(0.0)


# ── Forward transform: multi-day cumulative across a weekend ──────────────────


def test_forward_multi_day_cross_weekend():
    """With bushours=(9,17) the cumulative advances by 8/24 per business day.

    Thu (epoch) = 0, Fri = 8/24; weekend skipped → Mon = 16/24.
    """
    result = _fwd((9, 17), [dt.datetime(1970, 1, 5, 9)])  # Mon 09:00
    assert result == pytest.approx([16 / 24])


# ── Forward transform: per-day dict with explicit expected values ─────────────


def test_forward_per_day_dict_explicit():
    """Per-day dict: Thu has a short 0–8h session; Fri is full day.

    Thu 04:00 → 4/24, Thu 08:00 (close) → 8/24,
    Thu 12:00 (post-session) clips to 8/24,
    Fri 09:00 → cumulative(Fri) + 9/24 = 8/24 + 9/24.
    """
    dates = [
        dt.datetime(1970, 1, 1, 4),  # Thu 04:00 — 4h into [0, 8] session
        dt.datetime(1970, 1, 1, 8),  # Thu 08:00 — session close
        dt.datetime(1970, 1, 1, 12),  # Thu 12:00 — past session, clips
        dt.datetime(1970, 1, 2, 9),  # Fri 09:00 — full day, 9h in
    ]
    result = _fwd({"Thu": (0, 8)}, dates)
    assert result == pytest.approx([4 / 24, 8 / 24, 8 / 24, 8 / 24 + 9 / 24])


# ── Inverse transform: explicit busday-float → datetime ──────────────────────


def test_inverse_explicit_midday():
    """busday 4/24 with bushours=(9,17): 4h into the session = Thu 13:00."""
    inv = _inv((9, 17), [4 / 24]).astype("datetime64[s]").astype(object)
    assert inv[0] == dt.datetime(1970, 1, 1, 13)


def test_inverse_next_session_open():
    """busday 8/24 = one full Thu session elapsed → Fri 09:00 (next open)."""
    inv = _inv((9, 17), [8 / 24]).astype("datetime64[s]").astype(object)
    assert inv[0] == dt.datetime(1970, 1, 2, 9)


def test_inverse_at_morning_close_multi_interval():
    """busday 3/24 with [(9,12),(13,17)]: end of morning session → Thu 12:00.

    The lunch gap is collapsed, so the inverse at the gap boundary returns
    the end of the preceding interval (12:00), not the afternoon open.
    """
    inv = _inv([(9, 12), (13, 17)], [3 / 24]).astype("datetime64[s]").astype(object)
    assert inv[0] == dt.datetime(1970, 1, 1, 12)
