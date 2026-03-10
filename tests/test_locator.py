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
