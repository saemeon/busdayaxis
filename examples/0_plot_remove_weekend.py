"""# Remove Weekends

By default, weekends (Sat–Sun) are collapsed to zero width on the business axis.
The price line jumps directly from Friday close to Monday open,
eliminating the flat segments visible on the calendar axis.

Core code:

```python
ax.set_xscale("busday")
```
"""

# %%
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import busdayaxis

busdayaxis.register_scale()

num_days = 13
dates = pd.date_range("2025-01-02", periods=num_days * 24, freq="h")
returns = np.random.normal(0, 0.002, len(dates))
returns[dates.weekday >= 5] = 0.0
prices = 100 * (1 + pd.Series(returns, index=dates)).cumprod()


fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 7), sharey=True)

fig.suptitle(
    "Comparison of default (linear) scale vs scale='busday'",
    fontsize=14,
    fontweight="bold",
)

# --- Calendar axis ---
ax1.plot(dates, prices.values, linewidth=1.3)
ax1.set_title("default linear matplotlib scale")
ax1.xaxis.set_major_locator(mdates.DayLocator())
ax1.xaxis.set_major_formatter(mdates.DateFormatter("%a %d"))

# --- Business axis ---
ax2.plot(dates, prices.values, linewidth=1.3)
ax2.set_xscale("busday")
ax2.set_title("using `ax.set_xscale(scale='busday')`")
ax2.xaxis.set_major_locator(busdayaxis.DayLocator())
ax2.xaxis.set_major_formatter(mdates.DateFormatter("%a %d"))


# Shade weekends
full_days = pd.date_range(dates.min().normalize(), dates.max().normalize(), freq="D")
for d in full_days:
    if d.weekday() == 5:  # Saturday
        ax1.axvspan(d, d + pd.Timedelta(days=2), color="grey", alpha=0.15, linewidth=0)
# Mark weekend boundaries
for d in full_days:
    if d.weekday() == 5:
        ax2.axvline(d, linestyle="--", linewidth=0.8, alpha=0.6)
        ax2.axvline(d + pd.Timedelta(days=2), linestyle="--", linewidth=0.8, alpha=0.6)


_ = plt.tight_layout(rect=[0, 0, 1, 0.96])

# %%
