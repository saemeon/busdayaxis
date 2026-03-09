"""# Drawdown Chart

A drawdown chart shades the gap between the running price peak and the
current price using ``fill_between``. On the busday axis, the shaded
region has no weekend holes so peak-to-trough distances reflect real
trading time.

Core code:

```python
ax.set_xscale("busday")
ax.fill_between(dates, running_max, close, alpha=0.3, color="red", label="Drawdown")
```

Calendar axis:

- Price (plot)
- Running maximum (plot, dashed)
- Drawdown area (fill_between, red)

Business axis:

- Same artists, continuous shading without weekend gaps
"""

# %%
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import busdayaxis

busdayaxis.register_scale()

rng = np.random.default_rng(19)

num_days = 40
dates = pd.bdate_range("2025-01-01", periods=num_days)

# Random walk with a mid-period drawdown
returns = rng.normal(0.0005, 0.012, len(dates))
# Force a drawdown in the middle
returns[10:22] -= 0.015
close = pd.Series(100 * (1 + returns).cumprod(), index=dates)

running_max = close.cummax()

full_days = pd.date_range(dates.min().normalize(), dates.max().normalize(), freq="D")

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharey=True)
fig.suptitle("Drawdown Chart on busday Scale", fontsize=14, fontweight="bold")

ax2.set_xscale("busday")


def _draw(ax):
    ax.plot(dates, close.values, linewidth=1.2, color="steelblue", label="Close")
    ax.plot(
        dates,
        running_max.values,
        linewidth=1.0,
        linestyle="--",
        color="black",
        alpha=0.6,
        label="Running peak",
    )
    ax.fill_between(
        dates,
        running_max.values,
        close.values,
        alpha=0.3,
        color="red",
        label="Drawdown",
    )
    ax.set_ylabel("Price")
    ax.legend(fontsize=7, loc="upper left")


# --- Calendar axis ---
_draw(ax1)
ax1.set_title("Calendar Time (scale='linear')")
ax1.xaxis.set_major_locator(mdates.DayLocator())
ax1.xaxis.set_major_formatter(mdates.DateFormatter("%a %d %b"))
ax1.tick_params(axis="x", rotation=90)

for d in full_days:
    if d.weekday() == 5:  # Saturday
        ax1.axvspan(d, d + pd.Timedelta(days=2), color="grey", alpha=0.15, linewidth=0)

# --- Business axis ---
_draw(ax2)
ax2.set_title("Business Time (scale='busday')")
ax2.xaxis.set_major_locator(busdayaxis.DayLocator())
ax2.xaxis.set_major_formatter(mdates.DateFormatter("%a %d %b"))
ax2.tick_params(axis="x", rotation=90)

for d in full_days:
    if d.weekday() == 5:  # Saturday
        ax2.axvline(d, linestyle="--", linewidth=0.8, alpha=0.6)
        ax2.axvline(d + pd.Timedelta(days=2), linestyle="--", linewidth=0.8, alpha=0.6)

plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.show()

# %%
