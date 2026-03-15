"""# Per-Day Business Hours

Each weekday can be configured to have different bushours. To do so, pass a ``bushours``
dict where each key is a weekday name and the value is a tuple of
(start_hour, end_hour). On the business axis, days are scaled proportionally to their
total bushours length — i.e. days with less bushours will appear narrower.

Core code:

```python
ax.set_xscale("busday", bushours={
    "Mon": (9, 17),
    "Tue": (9, 17),
    "Wed": (9, 12),
    "Thu": (9, 22),
    "Fri": (9, 12),
})
```
"""

# %%
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import busdayaxis

busdayaxis.register_scale()

OPEN = 9

# define dummy data
bushours = {
    "Mon": (OPEN, 17),
    "Tue": (OPEN, 17),
    "Wed": (OPEN, 12),
    "Thu": (OPEN, 22),
    "Fri": (OPEN, 12),
}
_day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
close_per_wd = np.array([bushours.get(name, (0, 0))[1] for name in _day_names])
num_days = 5
dates = pd.date_range("2025-01-06", periods=num_days * 24, freq="h")  # Mon–Fri
close_hours = close_per_wd[dates.weekday]
returns = np.random.normal(0, 0.002, len(dates))
returns[~np.is_busday(np.array(dates, dtype="datetime64[D]"))] = 0.0
returns[(dates.hour <= OPEN) | (dates.hour > close_hours)] = 0.0
prices = (1 + pd.Series(returns, index=dates)).cumprod()


fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 7), sharey=True)
fig.suptitle("Per-Day Sessions: Mon/Tue 9–17, Wed/Fri 9–12, Thu 9–22", fontsize=13)

full_days = pd.date_range(dates.min().normalize(), dates.max().normalize(), freq="D")

# axis with default linear scale
ax1.plot(dates, prices.values, linewidth=1.3)
ax1.set_title("Calendar Time (scale='linear')")
ax1.set_ylabel("Price")
ax1.xaxis.set_major_locator(mdates.HourLocator())
ax1.xaxis.set_major_formatter(mdates.DateFormatter("%a %Hh"))
ax1.tick_params(axis="x", rotation=90)


# axis with business scale
ax2.plot(dates, prices.values, linewidth=1.3)
ax2.set_xscale("busday", bushours=bushours)
ax2.xaxis.set_major_locator(busdayaxis.HourLocator())
ax2.xaxis.set_major_formatter(mdates.DateFormatter("%a %Hh"))
ax2.set_title("Business Time (scale='busday', bushours={per-day})")
ax2.set_ylabel("Price")
ax2.tick_params(axis="x", rotation=90)

# Shade inactive periods per day
for d in full_days:
    close = close_per_wd[d.weekday()]
    ax1.axvspan(d, d + pd.Timedelta(hours=OPEN), color="grey", alpha=0.15, linewidth=0)
    ax1.axvspan(
        d + pd.Timedelta(hours=close),
        d + pd.Timedelta(hours=24),
        color="grey",
        alpha=0.15,
        linewidth=0,
    )
# Mark open/close boundaries
for d in full_days:
    close = close_per_wd[d.weekday()]
    ax2.axvline(d + pd.Timedelta(hours=OPEN), linestyle="--", linewidth=0.8, alpha=0.6)
    ax2.axvline(d + pd.Timedelta(hours=close), linestyle="--", linewidth=0.8, alpha=0.6)

_ = plt.tight_layout(rect=[0, 0, 1, 0.96])
