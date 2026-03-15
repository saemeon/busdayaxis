import pytest  # noqa


def test_busday_locator_import():
    from busdayaxis._locator import BusdayLocator

    locator = BusdayLocator()
    assert locator is not None


def test_busday_locator_with_axis():
    import matplotlib.pyplot as plt

    from busdayaxis._locator import BusdayLocator

    fig, ax = plt.subplots()
    locator = BusdayLocator()
    locator.set_axis(ax.xaxis)

    plt.close(fig)


def test_busday_locator_filters_outside_session():
    """BusdayLocator must discard ticks that fall outside the active session.

    With bushours=(9, 17), an HourLocator at every hour from 0–23 should
    return only ticks in [9, 17] on a business day.
    """
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    import pandas as pd

    import busdayaxis

    busdayaxis.register_scale()

    dates = pd.date_range("2025-01-06", periods=48, freq="h")  # Mon–Tue
    fig, ax = plt.subplots()
    ax.plot(dates, range(len(dates)))
    ax.set_xscale("busday", bushours=(9, 17))
    ax.xaxis.set_major_locator(busdayaxis.HourLocator(byhour=range(0, 24)))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H"))
    ax.set_xlim(
        mdates.date2num(pd.Timestamp("2025-01-06")),
        mdates.date2num(pd.Timestamp("2025-01-07")),
    )

    ticks = ax.xaxis.get_major_locator()()
    tick_dates = mdates.num2date(ticks)
    hours = [d.hour for d in tick_dates]

    # Hours should be within business hours 9-17 (day start at 0 is also allowed)
    assert all(0 <= h <= 17 for h in hours), (
        f"Expected only hours 0–17, got {sorted(set(hours))}"
    )
    # But no hours before 9 except day start
    assert all(h == 0 or h >= 9 for h in hours), (
        f"Expected day start (0) or hours >= 9, got {sorted(set(hours))}"
    )

    plt.close(fig)


def test_busday_locator_with_base_locator():
    """BusdayLocator wrapping a DayLocator returns one tick per business day."""
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    import pandas as pd

    import busdayaxis

    busdayaxis.register_scale()

    dates = pd.date_range("2025-01-06", periods=5, freq="B")  # Mon–Fri
    fig, ax = plt.subplots()
    ax.plot(dates, range(len(dates)))

    ax.xaxis.set_major_locator(busdayaxis.DayLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%a"))

    ax.set_xscale("busday")

    ticks = ax.xaxis.get_major_locator()()
    assert len(ticks) == 5, f"Expected 5 ticks for 5 business days, got {len(ticks)}"

    plt.close(fig)


def test_filter_ticks_empty():
    """_filter_ticks returns [] for empty input."""
    from busdayaxis._locator import BusdayLocator

    locator = BusdayLocator()
    assert locator._filter_ticks([]) == []


def test_keep_midnight_ticks_explicit_true():
    """keep_midnight_ticks=True always keeps midnight ticks."""
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    import pandas as pd

    import busdayaxis

    busdayaxis.register_scale()
    dates = pd.date_range("2025-01-06", periods=24, freq="h")
    fig, ax = plt.subplots()
    ax.plot(dates, range(len(dates)))
    ax.set_xscale("busday", bushours=(9, 17))
    ax.xaxis.set_major_locator(
        busdayaxis.HourLocator(byhour=range(0, 24), keep_midnight_ticks=True)
    )

    ticks = ax.xaxis.get_major_locator()()
    tick_hours = [mdates.num2date(t).hour for t in ticks]
    assert 0 in tick_hours

    plt.close(fig)


def test_keep_midnight_ticks_explicit_false():
    """keep_midnight_ticks=False suppresses midnight ticks."""
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    import pandas as pd

    import busdayaxis

    busdayaxis.register_scale()
    dates = pd.date_range("2025-01-06", periods=24, freq="h")
    fig, ax = plt.subplots()
    ax.plot(dates, range(len(dates)))
    ax.set_xscale("busday", bushours=(9, 17))
    ax.xaxis.set_major_locator(
        busdayaxis.HourLocator(byhour=range(0, 24), keep_midnight_ticks=False)
    )

    ticks = ax.xaxis.get_major_locator()()
    tick_hours = [mdates.num2date(t).hour for t in ticks]
    assert 0 not in tick_hours

    plt.close(fig)


def test_locator_delegate_methods():
    """set_tzinfo, datalim_to_dt, viewlim_to_dt, _get_unit, _get_interval,
    tick_values.
    """
    import datetime as dt

    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    import pandas as pd

    import busdayaxis

    busdayaxis.register_scale()
    dates = pd.date_range("2025-01-06", periods=5, freq="D")
    # Use a linear-scale axis so axis limits stay in matplotlib date space,
    # which datalim_to_dt / viewlim_to_dt require.
    fig, ax = plt.subplots()
    ax.plot(dates, range(5))

    locator = busdayaxis.BusdayLocator(mdates.DayLocator())
    locator.set_axis(ax.xaxis)

    vmin = mdates.date2num(dates[0].to_pydatetime())
    vmax = mdates.date2num(dates[-1].to_pydatetime())
    ax.set_xlim(vmin, vmax)

    locator.set_tzinfo(dt.timezone.utc)
    assert locator.datalim_to_dt() is not None
    assert locator.viewlim_to_dt() is not None
    assert locator._get_unit() is not None
    assert locator._get_interval() is not None
    assert locator() is not None

    plt.close(fig)


def test_locator_subclasses():
    """WeekdayLocator, MinuteLocator, SecondLocator, MicrosecondLocator instantiate."""
    import busdayaxis

    assert busdayaxis.WeekdayLocator() is not None
    assert busdayaxis.MinuteLocator() is not None
    assert busdayaxis.SecondLocator() is not None
    assert busdayaxis.MicrosecondLocator() is not None


def test_mid_busday_locator_no_axis():
    """MidBusdayLocator.__call__ returns [] when axis is None."""
    from busdayaxis._locator import MidBusdayLocator

    locator = MidBusdayLocator()
    assert locator() == []


def test_mid_busday_locator_tick_values():
    """MidBusdayLocator places one tick per business day at midpoint."""
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    import pandas as pd

    import busdayaxis

    busdayaxis.register_scale()
    dates = pd.date_range("2025-01-06", periods=5, freq="D")  # Mon–Fri
    fig, ax = plt.subplots()
    ax.plot(dates, range(5))
    ax.set_xscale("busday", bushours=(9, 17))
    ax.set_xlim(
        mdates.date2num(pd.Timestamp("2025-01-06")),
        mdates.date2num(pd.Timestamp("2025-01-10 23:59")),
    )
    ax.xaxis.set_minor_locator(busdayaxis.MidBusdayLocator())

    ticks = ax.xaxis.get_minor_locator()()
    assert len(ticks) == 5
    assert mdates.num2date(ticks[0]).hour == 13  # midpoint of 9–17

    plt.close(fig)


def test_mid_busday_locator_no_busdays():
    """MidBusdayLocator returns [] when the range contains no business days."""
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    import busdayaxis

    busdayaxis.register_scale()
    fig, ax = plt.subplots()
    ax.set_xscale("busday")

    locator = busdayaxis.MidBusdayLocator()
    locator.set_axis(ax.xaxis)

    sat = mdates.datestr2num("2025-01-04")
    sun = mdates.datestr2num("2025-01-05")
    assert locator.tick_values(sat, sun) == []

    plt.close(fig)
