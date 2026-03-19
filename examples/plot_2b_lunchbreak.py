"""# Multiple Intervals Per Day (Lunch Break)

``bushours`` accepts a list of ``(start, end)`` tuples to define multiple active
sessions per day. Gaps between intervals — such as a lunch break — are collapsed
on the axis just like overnight gaps or weekends.

Core code:

```python
ax.set_xscale("busday", bushours=[(9, 12), (13, 17)])
```
"""

# %%
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import busdayaxis

busdayaxis.register_scale()

MORNING_OPEN = 9
MORNING_CLOSE = 12
AFTERNOON_OPEN = 13
AFTERNOON_CLOSE = 17
bushours = [(MORNING_OPEN, MORNING_CLOSE), (AFTERNOON_OPEN, AFTERNOON_CLOSE)]

num_days = 3
dates = pd.date_range("2025-01-06", periods=num_days * 24 * 60, freq="min")
returns = np.random.normal(0, 0.002, len(dates))
in_session = (
    ((dates.hour >= MORNING_OPEN) & (dates.hour < MORNING_CLOSE))
    | ((dates.hour >= AFTERNOON_OPEN) & (dates.hour < AFTERNOON_CLOSE))
) & np.is_busday(np.array(dates, dtype="datetime64[D]"))
returns[~in_session] = 0.0
prices = (1 + pd.Series(returns, index=dates)).cumprod()

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 7), sharey=True)
fig.suptitle("Lunch Break (12:00–13:00) Collapsed", fontsize=14)

full_days = pd.date_range(dates.min().normalize(), dates.max().normalize(), freq="D")

# axis with default linear scale
ax1.plot(dates, prices.values, linewidth=1.3)
ax1.set_title("Calendar Time (scale='linear')")
ax1.set_ylabel("Price")
ax1.xaxis.set_major_locator(mdates.HourLocator())
ax1.xaxis.set_major_formatter(mdates.DateFormatter("%a %H"))
ax1.tick_params(axis="x", rotation=90)

for d in full_days:
    # pre-market
    ax1.axvspan(
        d, d + pd.Timedelta(hours=MORNING_OPEN), color="grey", alpha=0.15, linewidth=0
    )
    # lunch break
    ax1.axvspan(
        d + pd.Timedelta(hours=MORNING_CLOSE),
        d + pd.Timedelta(hours=AFTERNOON_OPEN),
        color="orange",
        alpha=0.2,
        linewidth=0,
    )
    # post-market
    ax1.axvspan(
        d + pd.Timedelta(hours=AFTERNOON_CLOSE),
        d + pd.Timedelta(hours=24),
        color="grey",
        alpha=0.15,
        linewidth=0,
    )

# axis with busday scale
ax2.plot(dates, prices.values, linewidth=1.3)
ax2.set_xscale("busday", bushours=bushours)
ax2.xaxis.set_major_locator(busdayaxis.HourLocator())
ax2.xaxis.set_major_formatter(mdates.DateFormatter("%a %H"))
ax2.set_title("Business Time (scale='busday', bushours=[(9, 12), (13, 17)])")
ax2.set_ylabel("Price")
ax2.tick_params(axis="x", rotation=90)

busdayaxis.mark_gaps(ax2, alpha=0.6)

_ = plt.tight_layout(rect=[0, 0, 1, 0.96])
