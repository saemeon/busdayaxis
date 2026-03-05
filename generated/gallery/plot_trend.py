"""# Trend Lines and Moving Average

Trend lines and moving averages maintain correct spacing on the busday
axis. Because non-trading days are compressed, the linear regression
slope reflects business-day time rather than calendar time, and the
moving average flows without weekend gaps.

Core code:

```python
ax.set_xscale("busday")
ax.plot(dates, trend, linestyle="--", label="Trend")
```

Calendar axis:

- Daily close price (plot)
- 10-day moving average (plot)
- Linear regression trend line (plot, dashed red)
- MA-crossover buy/sell signals (scatter)

Business axis:

- Same artists, weekends compressed — trend slope is undistorted
"""

# %%
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import busdayaxis

busdayaxis.register_scale()

rng = np.random.default_rng(7)

num_days = 30
dates = pd.bdate_range("2025-01-01", periods=num_days)

# Slight upward drift so the trend line is clearly visible
returns = rng.normal(0.001, 0.01, len(dates))
close = pd.Series(100 * (1 + returns).cumprod(), index=dates)

ma10 = close.rolling(10, min_periods=1).mean()

# Linear regression trend over the full period using integer day index as x
x = np.arange(len(close))
coeffs = np.polyfit(x, close.values, 1)
trend = np.poly1d(coeffs)(x)

# MA-crossover signals
prev_close = close.shift(1)
prev_ma10 = ma10.shift(1)
signal_up = dates[(close > ma10) & (prev_close <= prev_ma10)]
signal_dn = dates[(close < ma10) & (prev_close >= prev_ma10)]

full_days = pd.date_range(dates.min().normalize(), dates.max().normalize(), freq="D")

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharey=True)
fig.suptitle("Trend Lines and Moving Average on busday Scale", fontsize=14, fontweight="bold")

ax2.set_xscale("busday")


def _draw(ax):
    ax.plot(dates, close.values, linewidth=1.2, color="steelblue", label="Close")
    ax.plot(dates, ma10.values, linewidth=1.2, color="orange", label="MA(10)")
    ax.plot(dates, trend, linewidth=1.0, linestyle="--", color="red", alpha=0.8, label="Trend")
    ax.scatter(
        signal_up,
        close[signal_up].values,
        marker="^",
        color="green",
        s=60,
        zorder=5,
        label="Buy signal",
    )
    ax.scatter(
        signal_dn,
        close[signal_dn].values,
        marker="v",
        color="red",
        s=60,
        zorder=5,
        label="Sell signal",
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
ax2.xaxis.set_major_locator(busdayaxis.BusdayLocator(mdates.DayLocator()))
ax2.xaxis.set_major_formatter(mdates.DateFormatter("%a %d %b"))
ax2.tick_params(axis="x", rotation=90)

for d in full_days:
    if d.weekday() == 5:  # Saturday
        ax2.axvline(d, linestyle="--", linewidth=0.8, alpha=0.6)
        ax2.axvline(d + pd.Timedelta(days=2), linestyle="--", linewidth=0.8, alpha=0.6)

plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.show()

# %%
