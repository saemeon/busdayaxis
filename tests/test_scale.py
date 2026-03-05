import pytest

from busdayaxis._scale import _normalize_bushours


def test_import():
    import busdayaxis

    assert hasattr(busdayaxis, "BusdayScale")
    assert hasattr(busdayaxis, "BusdayLocator")


def test_busday_scale_registration():
    import busdayaxis as busdayaxis

    busdayaxis.register_scale()


# _normalize_bushours


def test_normalize_tuple_single():
    result = _normalize_bushours((9, 17))
    assert result == {i: (9, 17) for i in range(7)}


def test_normalize_list_of_seven():
    hours = [(9, 17), (9, 17), (9, 17), (9, 17), (9, 16), (0, 0), (0, 0)]
    result = _normalize_bushours(hours)
    assert result == {i: hours[i] for i in range(7)}


def test_normalize_dict_int_keys():
    result = _normalize_bushours(
        {0: (9, 17), 1: (9, 17), 2: (9, 17), 3: (9, 17), 4: (9, 16)}
    )
    assert result[0] == (9, 17)
    assert result[4] == (9, 16)
    assert result[5] == (0, 0)  # unspecified weekend defaults to closed
    assert result[6] == (0, 0)


def test_normalize_dict_with_weekend():
    result = _normalize_bushours({5: (10, 14)})
    assert result[5] == (10, 14)
    assert result[6] == (0, 0)  # Sunday not specified, defaults to closed


def test_normalize_dict_string_keys():
    result = _normalize_bushours({"Mon": (9, 17), "Fri": (9, 16)})
    assert result[0] == (9, 17)  # Mon
    assert result[4] == (9, 16)  # Fri
    assert result[1] == (0, 24)  # Tue — unspecified weekday → full day
    assert result[5] == (0, 0)  # Sat — unspecified weekend → closed


def test_normalize_dict_mixed_keys():
    result = _normalize_bushours({"Mon": (9, 17), 4: (9, 16)})
    assert result[0] == (9, 17)
    assert result[4] == (9, 16)


def test_normalize_invalid_hours_start_greater_than_end():
    with pytest.raises(ValueError, match="must satisfy 0 <= start <= end <= 24"):
        _normalize_bushours((17, 9))


def test_normalize_invalid_hours_negative():
    with pytest.raises(ValueError, match="must satisfy 0 <= start <= end <= 24"):
        _normalize_bushours((-1, 17))


def test_normalize_invalid_hours_greater_than_24():
    with pytest.raises(ValueError, match="must satisfy 0 <= start <= end <= 24"):
        _normalize_bushours((9, 25))


def test_normalize_invalid_dict_key_int():
    with pytest.raises(ValueError, match="expected int 0-6"):
        _normalize_bushours({7: (9, 17)})


def test_normalize_invalid_dict_key_string():
    with pytest.raises(ValueError, match="expected int 0-6"):
        _normalize_bushours({"Monday": (9, 17)})


def test_normalize_invalid_type():
    with pytest.raises(ValueError, match="bushours must be"):
        _normalize_bushours("invalid")


# BusdayScale


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


def test_custom_weekmask():
    """Custom weekmask (GCC Sun–Thu): Friday (off-day) must roll to Sunday,
    so its axis position equals Sunday's. Previously broken because off-days
    were hardcoded to Sat/Sun regardless of the weekmask kwarg."""
    import matplotlib.pyplot as plt
    import pandas as pd

    from busdayaxis._scale import (
        _build_weighted_calendar,
        _bushours_bounds,
        _datetime_to_busday_float,
        _normalize_bushours,
    )

    bushours_dict = _normalize_bushours((0, 24))
    gcc = dict(weekmask="Sun Mon Tue Wed Thu")
    starts, ends = _bushours_bounds(bushours_dict)
    weights = ends - starts
    calendar_days, cumulative = _build_weighted_calendar(weights, **gcc)

    thu = pd.DatetimeIndex(["2024-01-04"])  # last GCC business day before weekend
    fri = pd.DatetimeIndex(["2024-01-05"])  # GCC off-day (Fri)
    sat = pd.DatetimeIndex(["2024-01-06"])  # GCC off-day (Sat)
    sun = pd.DatetimeIndex(["2024-01-07"])  # first GCC business day of next week

    pos_thu = _datetime_to_busday_float(
        thu, bushours_dict, calendar_days, cumulative, weights
    )
    pos_fri = _datetime_to_busday_float(
        fri, bushours_dict, calendar_days, cumulative, weights
    )
    pos_sat = _datetime_to_busday_float(
        sat, bushours_dict, calendar_days, cumulative, weights
    )
    pos_sun = _datetime_to_busday_float(
        sun, bushours_dict, calendar_days, cumulative, weights
    )

    # Fri and Sat roll forward to Sun — all three must share the same position
    assert pos_fri[0] == pos_sun[0], "GCC Friday must map to start of Sunday"
    assert pos_sat[0] == pos_sun[0], "GCC Saturday must map to start of Sunday"
    # Sunday is exactly 1 business day after Thursday
    assert pos_sun[0] == pos_thu[0] + 1

    # Smoke-test that plotting doesn't raise with a custom weekmask
    dates = pd.date_range("2024-01-01", periods=14, freq="D")
    fig, ax = plt.subplots()
    ax.plot(dates, range(len(dates)))
    ax.set_xscale("busday", weekmask="Sun Mon Tue Wed Thu")
    plt.close(fig)


def test_holidays_do_not_bleed_into_next_day():
    """A data point on a public holiday must map to the same axis position as
    the *following* business day (rolled forward), not fall between two days."""
    import pandas as pd

    from busdayaxis._scale import (
        _build_weighted_calendar,
        _bushours_bounds,
        _datetime_to_busday_float,
        _normalize_bushours,
    )

    bushours_dict = _normalize_bushours((0, 24))
    holiday = "2024-01-15"  # MLK Day (Monday)
    next_busday = "2024-01-16"  # Tuesday
    starts, ends = _bushours_bounds(bushours_dict)
    weights = ends - starts
    calendar_days, cumulative = _build_weighted_calendar(weights, holidays=[holiday])

    pos_holiday = _datetime_to_busday_float(
        pd.DatetimeIndex([holiday]), bushours_dict, calendar_days, cumulative, weights
    )
    pos_next = _datetime_to_busday_float(
        pd.DatetimeIndex([next_busday]),
        bushours_dict,
        calendar_days,
        cumulative,
        weights,
    )

    # Holiday (rolled forward to Tuesday) should equal start of that Tuesday
    assert pos_holiday[0] == pos_next[0], (
        f"Holiday pos {pos_holiday[0]} should equal next busday pos {pos_next[0]}"
    )


def test_busdaycal_parameter():
    """busdaycal overrides weekmask and holidays; the scale must accept it."""
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd

    cal = np.busdaycalendar(weekmask="1111100", holidays=["2024-12-25"])
    dates = pd.date_range("2024-12-23", periods=7, freq="D")

    fig, ax = plt.subplots()
    ax.plot(dates, range(len(dates)))
    ax.set_xscale("busday", busdaycal=cal)
    plt.close(fig)


def test_per_day_bushours_day_widths():
    """Days with longer sessions must occupy more space on the axis.

    Thursday (9–22 = 13 h) must be wider than Wednesday (9–12 = 3 h)
    and Monday (9–17 = 8 h) must fall in between.
    """
    import pandas as pd

    from busdayaxis._scale import (
        _build_weighted_calendar,
        _bushours_bounds,
        _datetime_to_busday_float,
        _normalize_bushours,
    )

    bushours = {
        "Mon": (9, 17),  # 8 h
        "Wed": (9, 12),  # 3 h
        "Thu": (9, 22),  # 13 h
    }
    bushours_dict = _normalize_bushours(bushours)
    weekmask = "".join(
        "1" if bushours_dict[i][1] > bushours_dict[i][0] else "0" for i in range(7)
    )
    starts, ends = _bushours_bounds(bushours_dict)
    weights = ends - starts
    calendar_days, cumulative = _build_weighted_calendar(weights, weekmask=weekmask)

    def width(open_str, close_str):
        t_open = pd.DatetimeIndex([open_str])
        t_close = pd.DatetimeIndex([close_str])
        pos_o = _datetime_to_busday_float(
            t_open,
            bushours_dict,
            calendar_days,
            cumulative,
            weights,
            weekmask=weekmask,
        )
        pos_c = _datetime_to_busday_float(
            t_close,
            bushours_dict,
            calendar_days,
            cumulative,
            weights,
            weekmask=weekmask,
        )
        return pos_c[0] - pos_o[0]

    w_mon = width("2025-01-06 09:00", "2025-01-06 17:00")  # Monday 8 h
    w_wed = width("2025-01-08 09:00", "2025-01-08 12:00")  # Wednesday 3 h
    w_thu = width("2025-01-09 09:00", "2025-01-09 22:00")  # Thursday 13 h

    assert w_thu > w_mon > w_wed, (
        f"Expected thu({w_thu:.3f}) > mon({w_mon:.3f}) > wed({w_wed:.3f})"
    )


def test_bushours_uniform_overnight_compression():
    """With bushours=(9, 17), timestamps outside business hours must map to
    the same axis position as the session boundary they were clipped to."""
    import pandas as pd

    from busdayaxis._scale import (
        _build_weighted_calendar,
        _bushours_bounds,
        _datetime_to_busday_float,
        _normalize_bushours,
    )

    bushours_dict = _normalize_bushours((9, 17))
    starts, ends = _bushours_bounds(bushours_dict)
    weights = ends - starts
    calendar_days, cumulative = _build_weighted_calendar(weights, weekmask="1111100")

    kwargs = dict(
        bushours_dict=bushours_dict,
        calendar_days=calendar_days,
        cumulative=cumulative,
        weights=weights,
        weekmask="1111100",
    )

    open_ = pd.DatetimeIndex(["2025-01-06 09:00"])  # Mon open
    before = pd.DatetimeIndex(["2025-01-06 07:00"])  # pre-market → clipped to open
    close = pd.DatetimeIndex(["2025-01-06 17:00"])  # Mon close
    after = pd.DatetimeIndex(["2025-01-06 20:00"])  # after-hours → clipped to close

    pos_open = _datetime_to_busday_float(open_, **kwargs)
    pos_before = _datetime_to_busday_float(before, **kwargs)
    pos_close = _datetime_to_busday_float(close, **kwargs)
    pos_after = _datetime_to_busday_float(after, **kwargs)

    assert pos_before[0] == pos_open[0], "Pre-market must clip to session open"
    assert pos_after[0] == pos_close[0], "After-hours must clip to session close"
    assert pos_close[0] > pos_open[0], "Close must be after open on the axis"
