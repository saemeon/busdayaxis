import pytest  # noqa


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


def test_bushours_list():
    """List of 7 tuples for each weekday."""
    import matplotlib.pyplot as plt
    import pandas as pd

    hours = [(9, 17)] * 5 + [(0, 0), (0, 0)]  # Mon-Fri 9-17, weekends closed

    dates = pd.date_range("2024-01-01", periods=10, freq="D")
    values = range(len(dates))

    fig, ax = plt.subplots()
    ax.plot(dates, values)
    ax.set_xscale("busday", bushours=hours)

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
