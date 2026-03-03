import pytest  # noqa


def test_import():
    import mplbusdayaxis

    assert hasattr(mplbusdayaxis, "BusdayScale")
    assert hasattr(mplbusdayaxis, "BusdayLocator")


def test_busday_scale_registration():
    import mplbusdayaxis as mplbusdayaxis

    mplbusdayaxis.register_scale()


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
