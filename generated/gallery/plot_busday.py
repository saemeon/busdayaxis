"""# Exclude Extra Holidays

A specific date is passed via ``holidays`` and collapsed on the business axis,
identical to a weekend. The calendar axis highlights the holiday in red; the
business axis removes it entirely so the surrounding days are adjacent.

Core code:

```python
ax.set_xscale("busday", holidays=["2025-01-06"])
```
"""

# %%
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import busdayaxis

busdayaxis.register_scale()

holiday = "2025-01-06"  # Monday

num_days = 10
dates = pd.date_range("2025-01-01", periods=num_days * 24, freq="h")

returns = np.random.normal(0, 0.002, len(dates))
returns[dates.weekday >= 5] = 0.0
returns[dates.normalize() == pd.Timestamp(holiday)] = 0.0

prices = 100 * (1 + pd.Series(returns, index=dates)).cumprod()

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 7), sharey=True)
fig.suptitle("Excluding Holidays", fontsize=14, fontweight="bold")

full_days = pd.date_range(dates.min().normalize(), dates.max().normalize(), freq="D")

# --- Calendar axis ---
ax1.plot(dates, prices.values, linewidth=1.3)
ax1.set_title("Calendar Time (scale='linear')")
ax1.set_ylabel("Price")
ax1.xaxis.set_major_locator(mdates.DayLocator())
ax1.xaxis.set_major_formatter(mdates.DateFormatter("%a %d %b"))
ax1.tick_params(axis="x", rotation=90)

# Shade weekends
for d in full_days:
    if d.weekday() == 5:  # Saturday
        ax1.axvspan(d, d + pd.Timedelta(days=2), color="grey", alpha=0.15, linewidth=0)

# Shade holiday
ax1.axvspan(
    pd.Timestamp(holiday),
    pd.Timestamp(holiday) + pd.Timedelta(days=1),
    color="tomato",
    alpha=0.3,
    linewidth=0,
    label=f"Holiday ({holiday})",
)
ax1.legend(loc="upper left", fontsize=8)

# --- Business axis ---
ax2.plot(dates, prices.values, linewidth=1.3)
ax2.set_xscale("busday", holidays=[holiday])
ax2.set_title(f"Business Time (scale='busday', holidays=['{holiday}'])")
ax2.set_ylabel("Price")
ax2.xaxis.set_major_locator(busdayaxis.BusdayLocator(mdates.DayLocator()))
ax2.xaxis.set_major_formatter(mdates.DateFormatter("%a %d %b"))
ax2.tick_params(axis="x", rotation=90)

# Mark weekend boundaries
for d in full_days:
    if d.weekday() == 5:
        ax2.axvline(d, linestyle="--", linewidth=0.8, alpha=0.6)
        ax2.axvline(d + pd.Timedelta(days=2), linestyle="--", linewidth=0.8, alpha=0.6)

plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.show()

# %%
