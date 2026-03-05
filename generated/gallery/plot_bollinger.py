"""# Bollinger Bands

Bollinger Bands (20-day SMA ± 2σ) applied to daily closing prices.
On the calendar axis, weekend gaps interrupt the filled band; on the
busday axis the bands flow continuously, making mean-reversion and
volatility patterns easier to read.

Core code:

```python
ax.set_xscale("busday")
ax.fill_between(dates, lower, upper, alpha=0.2, label="Band (±2σ)")
```

Calendar axis:

- Daily close price (plot)
- 20-day SMA (plot)
- Bollinger Bands (fill_between, ±2σ)
- Breakout points above/below band (scatter)

Business axis:

- Same artists, continuous bands without weekend gaps
"""

# %%
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import busdayaxis

busdayaxis.register_scale()

rng = np.random.default_rng(11)

# 50 days: first 20 build the MA warmup; rest is the interesting region
dates = pd.bdate_range("2024-11-01", periods=50)

returns = rng.normal(0, 0.012, len(dates))
close = pd.Series(100 * (1 + returns).cumprod(), index=dates)

sma = close.rolling(20, min_periods=1).mean()
std = close.rolling(20, min_periods=1).std().fillna(0)
upper = sma + 2 * std
lower = sma - 2 * std

above_band = close[close > upper]
below_band = close[close < lower]

full_days = pd.date_range(dates.min().normalize(), dates.max().normalize(), freq="D")

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharey=True)
fig.suptitle("Bollinger Bands on busday Scale", fontsize=14, fontweight="bold")

ax2.set_xscale("busday")


def _draw(ax):
    ax.fill_between(
        dates,
        lower.values,
        upper.values,
        alpha=0.15,
        color="steelblue",
        label="Band (±2σ)",
    )
    ax.plot(dates, sma.values, linewidth=1.2, color="orange", label="SMA(20)")
    ax.plot(dates, close.values, linewidth=1.0, color="steelblue", alpha=0.9, label="Close")
    ax.scatter(
        above_band.index,
        above_band.values,
        marker="v",
        color="red",
        s=40,
        zorder=5,
        label="Above upper band",
    )
    ax.scatter(
        below_band.index,
        below_band.values,
        marker="^",
        color="green",
        s=40,
        zorder=5,
        label="Below lower band",
    )
    ax.set_ylabel("Price")
    ax.legend(fontsize=7, loc="upper left")


# --- Calendar axis ---
_draw(ax1)
ax1.set_title("Calendar Time (scale='linear')")
ax1.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO))
ax1.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
ax1.tick_params(axis="x", rotation=45)

for d in full_days:
    if d.weekday() == 5:  # Saturday
        ax1.axvspan(d, d + pd.Timedelta(days=2), color="grey", alpha=0.15, linewidth=0)

# --- Business axis ---
_draw(ax2)
ax2.set_title("Business Time (scale='busday')")
ax2.xaxis.set_major_locator(
    busdayaxis.BusdayLocator(mdates.WeekdayLocator(byweekday=mdates.MO))
)
ax2.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
ax2.tick_params(axis="x", rotation=45)

for d in full_days:
    if d.weekday() == 5:  # Saturday
        ax2.axvline(d, linestyle="--", linewidth=0.8, alpha=0.6)
        ax2.axvline(d + pd.Timedelta(days=2), linestyle="--", linewidth=0.8, alpha=0.6)

plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.show()

# %%
