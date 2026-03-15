import datetime as dt

import pytest  # noqa

from busdayaxis._scale import _coerce_hour_span, _to_hour_float


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


def test_coerce_hour_span_floats():
    assert _coerce_hour_span((9, 17)) == (9.0, 17.0)


def test_coerce_hour_span_strings():
    assert _coerce_hour_span(("09:00", "17:00")) == (9.0, 17.0)


def test_coerce_hour_span_time_objects():
    assert _coerce_hour_span((dt.time(9), dt.time(17))) == (9.0, 17.0)


def test_coerce_hour_span_mixed():
    assert _coerce_hour_span((9, "17:30")) == (9.0, 17.5)


def test_coerce_hour_span_invalid_order():
    with pytest.raises(ValueError):
        _coerce_hour_span((17, 9))


def test_coerce_hour_span_out_of_range():
    with pytest.raises(ValueError):
        _coerce_hour_span((0, 25))


def test_coerce_hour_span_wrong_length():
    with pytest.raises(ValueError):
        _coerce_hour_span((9, 17, 5))  # type: ignore[arg-type]


def test_normalize_bushours_int_key():
    from busdayaxis._scale import _normalize_bushours

    result = _normalize_bushours({0: (9, 17), 4: (9, 13)})
    assert result[0] == (9.0, 17.0)
    assert result[4] == (9.0, 13.0)


def test_normalize_bushours_invalid_key():
    from busdayaxis._scale import _normalize_bushours

    with pytest.raises(ValueError):
        _normalize_bushours({"Funday": (9, 17)})  # type: ignore[arg-type]


def test_normalize_bushours_invalid_input():
    from busdayaxis._scale import _normalize_bushours

    with pytest.raises(ValueError):
        _normalize_bushours((9, 17, 5))  # type: ignore[arg-type]


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
