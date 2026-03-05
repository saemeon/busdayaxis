"""# Per-Day Business Hours

Each weekday can have a different session via a ``bushours`` dict.
On the business axis, days are scaled proportionally to their session
length — Thursday (13 h) is visibly wider than Wednesday or Friday (3 h each).

Core code:

```python
ax.set_xscale("busday", bushours={
    "Mon": (9, 17), "Tue": (9, 17),
    "Wed": (9, 12), "Thu": (9, 22), "Fri": (9, 12),
})
```

Calendar axis:

- Hourly ticks
- Per-day inactive period shading

Business axis:

- Each day proportional to its session length
"""

# %%
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import busdayaxis

busdayaxis.register_scale()

OPEN = 9
CLOSE_REGULAR = 17
CLOSE_MIDDAY = 12
CLOSE_LATE = 22
bushours = {
    "Mon": (OPEN, CLOSE_REGULAR),
    "Tue": (OPEN, CLOSE_REGULAR),
    "Wed": (OPEN, CLOSE_MIDDAY),
    "Thu": (OPEN, CLOSE_LATE),
    "Fri": (OPEN, CLOSE_MIDDAY),
}

# Derive close hour per weekday (Mon=0..Sun=6) directly from bushours
_day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
close_per_wd = np.array([bushours.get(name, (0, 0))[1] for name in _day_names])

num_days = 5
dates = pd.date_range("2025-01-06", periods=num_days * 24, freq="h")  # Mon–Fri

returns = np.random.normal(0, 0.002, len(dates))
close_hours = close_per_wd[dates.weekday]
returns[(dates.hour < OPEN) | (dates.hour >= close_hours)] = 0.0

prices = 100 * (1 + pd.Series(returns, index=dates)).cumprod()

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 7), sharey=True)
fig.suptitle(
    "Per-Day Sessions: Mon/Tue 9–17, Wed/Fri 9–12, Thu 9–22",
    fontsize=13,
    fontweight="bold",
)

full_days = pd.date_range(dates.min().normalize(), dates.max().normalize(), freq="D")
tick_hours = range(OPEN, int(close_per_wd.max()) + 1, 2)

# --- Calendar axis ---
ax1.plot(dates, prices.values, linewidth=1.3)
ax1.set_title("Calendar Time (scale='linear')")
ax1.set_ylabel("Price")
ax1.xaxis.set_major_locator(mdates.HourLocator())
ax1.xaxis.set_major_formatter(mdates.DateFormatter("%a %H:%M"))
ax1.tick_params(axis="x", rotation=90)

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

# --- Business axis ---
ax2.plot(dates, prices.values, linewidth=1.3)

# Set locators BEFORE scale to avoid AutoDateLocator generating too many ticks
ax2.xaxis.set_major_locator(busdayaxis.BusdayLocator(mdates.HourLocator()))
ax2.xaxis.set_major_formatter(mdates.DateFormatter("%a %H:%M"))

ax2.set_xscale("busday", bushours=bushours)
ax2.set_title("Business Time (scale='busday', bushours={per-day})")
ax2.set_ylabel("Price")
ax2.tick_params(axis="x", rotation=90)

# Mark open/close boundaries
for d in full_days:
    close = close_per_wd[d.weekday()]
    ax2.axvline(d + pd.Timedelta(hours=OPEN), linestyle="--", linewidth=0.8, alpha=0.6)
    ax2.axvline(d + pd.Timedelta(hours=close), linestyle="--", linewidth=0.8, alpha=0.6)

plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.show()

# %%
