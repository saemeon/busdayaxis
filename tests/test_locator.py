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
    ax.xaxis.set_major_locator(
        busdayaxis.BusdayLocator(mdates.HourLocator(byhour=range(0, 24)))
    )
    ax.set_xlim(
        mdates.date2num(pd.Timestamp("2025-01-06")),
        mdates.date2num(pd.Timestamp("2025-01-07")),
    )

    ticks = ax.xaxis.get_major_locator()()
    tick_dates = mdates.num2date(ticks)
    hours = [d.hour for d in tick_dates]

    assert all(9 <= h <= 17 for h in hours), (
        f"Expected only hours 9–17, got {sorted(set(hours))}"
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
    ax.set_xscale("busday")
    ax.xaxis.set_major_locator(busdayaxis.BusdayLocator(mdates.DayLocator()))

    ticks = ax.xaxis.get_major_locator()()
    assert len(ticks) == 5, f"Expected 5 ticks for 5 business days, got {len(ticks)}"

    plt.close(fig)
