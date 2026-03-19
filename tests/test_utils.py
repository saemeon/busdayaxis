import pytest

import busdayaxis
from busdayaxis._utils import mark_gaps

# ── holidays_from_exchange — real calendars ───────────────────────────────────

# NYSE holidays in January 2025 that fall on weekdays:
#   2025-01-01  New Year's Day  (Wednesday)
#   2025-01-20  MLK Jr. Day     (Monday)
_NYSE_JAN_2025_HOLIDAYS = {"2025-01-01", "2025-01-20"}
_NYSE_JAN_2025_TRADING_DAY = "2025-01-02"  # first trading day of 2025


def test_holidays_from_exchange_real_pmcal():
    """pandas_market_calendars NYSE: known holidays present, trading days absent."""
    pmcal = pytest.importorskip("pandas_market_calendars")
    cal = pmcal.get_calendar("NYSE")
    result = set(busdayaxis.holidays_from_exchange(cal, "2025-01-01", "2025-01-31"))
    assert _NYSE_JAN_2025_HOLIDAYS <= result
    assert _NYSE_JAN_2025_TRADING_DAY not in result


def test_holidays_from_exchange_real_xcal():
    """exchange_calendars XNYS: known holidays present, trading days absent."""
    xcals = pytest.importorskip("exchange_calendars")
    cal = xcals.get_calendar("XNYS")
    result = set(busdayaxis.holidays_from_exchange(cal, "2025-01-01", "2025-01-31"))
    assert _NYSE_JAN_2025_HOLIDAYS <= result
    assert _NYSE_JAN_2025_TRADING_DAY not in result


def test_holidays_from_exchange_pmcal_xcal_agree():
    """Both calendar libraries return the same holidays for NYSE January 2025."""
    pmcal = pytest.importorskip("pandas_market_calendars")
    xcals = pytest.importorskip("exchange_calendars")
    pmcal_result = set(
        busdayaxis.holidays_from_exchange(
            pmcal.get_calendar("NYSE"), "2025-01-01", "2025-01-31"
        )
    )
    xcal_result = set(
        busdayaxis.holidays_from_exchange(
            xcals.get_calendar("XNYS"), "2025-01-01", "2025-01-31"
        )
    )
    assert pmcal_result == xcal_result


# ── holidays_from_exchange — mock calendars ───────────────────────────────────


def _make_mock_pmcal(excluded="2025-01-03"):
    """Mock pandas_market_calendars calendar (start_date/end_date kwargs)."""
    import pandas as pd

    class _Mock:
        def schedule(self, start_date, end_date):
            dates = pd.bdate_range(start_date, end_date)
            return pd.DataFrame(index=dates[dates != excluded])

    return _Mock()


def _make_mock_xcal(excluded="2025-01-03"):
    """Mock exchange_calendars calendar (start/end kwargs)."""
    import pandas as pd

    class _Mock:
        def schedule(self, start, end):
            dates = pd.bdate_range(start, end)
            return pd.DataFrame(index=dates[dates != excluded])

    return _Mock()


def test_holidays_from_exchange_pmcal_interface():
    """Works with pandas_market_calendars-style start_date/end_date kwargs."""
    result = busdayaxis.holidays_from_exchange(
        _make_mock_pmcal(), "2025-01-01", "2025-01-10"
    )
    assert "2025-01-03" in result  # excluded Friday treated as holiday
    assert "2025-01-06" not in result  # Monday is a normal trading day


def test_holidays_from_exchange_xcal_interface():
    """Works with exchange_calendars-style start/end kwargs."""
    result = busdayaxis.holidays_from_exchange(
        _make_mock_xcal(), "2025-01-01", "2025-01-10"
    )
    assert "2025-01-03" in result
    assert "2025-01-06" not in result


def test_holidays_from_exchange_returns_strings():
    result = busdayaxis.holidays_from_exchange(
        _make_mock_pmcal(), "2025-01-01", "2025-01-31"
    )
    assert all(isinstance(h, str) for h in result)
    assert all(len(h) == 10 for h in result)  # "YYYY-MM-DD"


def test_holidays_from_exchange_invalid_calendar():
    """Raises ValueError for an object with no usable schedule() method."""

    class _Bad:
        pass

    with pytest.raises(ValueError):
        busdayaxis.holidays_from_exchange(_Bad(), "2025-01-01", "2025-12-31")


def test_holidays_from_exchange_empty_range():
    """Returns [] when the range contains no weekdays."""
    result = busdayaxis.holidays_from_exchange(
        _make_mock_pmcal(),
        "2025-01-04",
        "2025-01-05",  # Sat–Sun only
    )
    assert result == []


# ── mark_gaps helpers ─────────────────────────────────────────────────────────


def _make_busday_ax(bushours=(9, 17)):
    """Return (fig, ax) with busday scale and an explicit Mon–Fri xlim."""
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    import pandas as pd

    busdayaxis.register_scale()
    dates = pd.date_range("2025-01-06", periods=5 * 24, freq="h")  # Mon–Fri
    fig, ax = plt.subplots()
    ax.plot(dates, range(len(dates)))
    ax.set_xscale("busday", bushours=bushours)
    # Set xlim explicitly in data coords (mpl date numbers) to avoid
    # auto-scale padding pulling in extra business days.
    ax.set_xlim(
        mdates.date2num(pd.Timestamp("2025-01-06")),
        mdates.date2num(pd.Timestamp("2025-01-10 23:59")),
    )
    return fig, ax


# ── mark_gaps: input validation ───────────────────────────────────────────────


def test_mark_gaps_invalid_style():
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    with pytest.raises(ValueError, match="style"):
        mark_gaps(ax, style="shaded")
    plt.close(fig)


def test_mark_gaps_non_busday_axis():
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()  # default linear scale
    with pytest.raises(ValueError, match="busday"):
        mark_gaps(ax)
    plt.close(fig)


# ── mark_gaps: vline ──────────────────────────────────────────────────────────


def test_mark_gaps_vline_returns_artists():
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    fig, ax = _make_busday_ax()
    artists = mark_gaps(ax, style="vline")
    assert len(artists) > 0
    assert all(isinstance(a, Line2D) for a in artists)
    plt.close(fig)


def test_mark_gaps_vline_count_single_interval():
    """One gap per business day with bushours=(9,17): 5 days → 5 vlines."""
    import matplotlib.pyplot as plt

    fig, ax = _make_busday_ax(bushours=(9, 17))
    artists = mark_gaps(ax, style="vline")
    assert len(artists) == 5
    plt.close(fig)


def test_mark_gaps_vline_count_multi_interval():
    """Two intervals per day → 2 gaps per day → 10 vlines for 5 days."""
    import matplotlib.pyplot as plt

    fig, ax = _make_busday_ax(bushours=[(9, 12), (13, 17)])
    artists = mark_gaps(ax, style="vline")
    assert len(artists) == 10
    plt.close(fig)


def test_mark_gaps_vline_kwargs_forwarded():
    """Custom color and linestyle are applied to vline artists."""
    import matplotlib.pyplot as plt

    fig, ax = _make_busday_ax()
    artists = mark_gaps(ax, style="vline", color="red", linestyle=":")
    line = artists[0]
    assert line.get_color() == "red"
    assert line.get_linestyle() == ":"
    plt.close(fig)


# ── mark_gaps: broken ─────────────────────────────────────────────────────────


def test_mark_gaps_broken_returns_artists():
    import matplotlib.pyplot as plt

    fig, ax = _make_busday_ax()
    artists = mark_gaps(ax, style="broken")
    assert len(artists) > 0
    plt.close(fig)


def test_mark_gaps_broken_count():
    """Broken style draws 2 marks per gap (top + bottom)."""
    import matplotlib.pyplot as plt

    fig, ax = _make_busday_ax(bushours=(9, 17))
    artists = mark_gaps(ax, style="broken")
    # 5 gaps × 2 marks each
    assert len(artists) == 10
    plt.close(fig)


# ── mark_gaps: both ───────────────────────────────────────────────────────────


def test_mark_gaps_both_count():
    """'both' adds vlines + broken marks."""
    import matplotlib.pyplot as plt

    fig, ax = _make_busday_ax(bushours=(9, 17))
    artists = mark_gaps(ax, style="both")
    # 5 vlines + 5*2 broken marks
    assert len(artists) == 15
    plt.close(fig)


# ── mark_gaps: edge cases ─────────────────────────────────────────────────────


def test_mark_gaps_returns_empty_when_no_gaps():
    """Returns [] when the view contains no business days."""
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    import pandas as pd

    busdayaxis.register_scale()
    fig, ax = plt.subplots()
    ax.set_xscale("busday")
    # Set xlim in data coords (mpl date numbers) to a Sat–Sun range
    ax.set_xlim(
        mdates.date2num(pd.Timestamp("2025-01-04")),
        mdates.date2num(pd.Timestamp("2025-01-05")),
    )
    artists = mark_gaps(ax)
    assert artists == []
    plt.close(fig)


def test_mark_gaps_size_kwarg():
    """size kwarg is accepted for broken style without error."""
    import matplotlib.pyplot as plt

    fig, ax = _make_busday_ax()
    artists = mark_gaps(ax, style="broken", size=14)
    assert len(artists) > 0
    plt.close(fig)
