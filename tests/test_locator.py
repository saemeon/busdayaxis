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
