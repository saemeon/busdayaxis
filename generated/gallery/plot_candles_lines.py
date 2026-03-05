"""# Candlestick Chart with Trader Lines

Support and resistance trend lines are drawn using ``plot``, and
horizontal key levels use ``axhline``. On the busday axis the lines
span only trading time, so their visual slope reflects business-day
intervals rather than calendar days.

Core code:

```python
ax.set_xscale("busday")
# Trend line between two price pivots, extended to a future business date
ax.plot([pivot_date1, future_date], [pivot_price1, extrapolated_price], "--")
```

Calendar axis:

- Candlestick price
- Support trend line (green dashed) connecting two reaction lows
- Resistance trend line (red dashed) connecting two reaction highs
- Horizontal key level (axhline)

Business axis:

- Same lines — slopes reflect true business-day time
"""

# %%
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import busdayaxis

busdayaxis.register_scale()

rng = np.random.default_rng(55)

dates = pd.bdate_range("2025-01-01", periods=25)
draw_times = dates + pd.Timedelta(hours=12)

# Upward-drifting price so a rising support line is visible
returns = rng.normal(0.002, 0.012, len(dates))
close = 100 * (1 + pd.Series(returns, index=dates)).cumprod()
open_ = close.shift(1).fillna(100)
high = np.maximum(open_.values, close.values) + rng.uniform(0.1, 0.7, len(dates))
low = np.minimum(open_.values, close.values) - rng.uniform(0.1, 0.7, len(dates))

colors = ["green" if c >= o else "red" for c, o in zip(close.values, open_.values)]
body_bottom = np.minimum(open_.values, close.values)
body_height = np.abs(close.values - open_.values)

n = len(dates)

# --- Support trend line: two lowest lows in separate thirds ---
i1_sup = np.argmin(low[: n // 3])
i2_sup = n // 3 + np.argmin(low[n // 3 : 2 * n // 3])
slope_sup = (low[i2_sup] - low[i1_sup]) / (i2_sup - i1_sup)
# Extend to 4 business days beyond the last candle
extend_days = 4
future_date = dates[-1] + pd.offsets.BDay(extend_days)
y_sup_start = low[i1_sup]
y_sup_end = y_sup_start + slope_sup * (n - 1 + extend_days - i1_sup)

# --- Resistance trend line: two highest highs in first half ---
i1_res = np.argmax(high[: n // 4])
i2_res = n // 4 + np.argmax(high[n // 4 : n // 2])
slope_res = (high[i2_res] - high[i1_res]) / (i2_res - i1_res)
y_res_start = high[i1_res]
y_res_end = y_res_start + slope_res * (n - 1 + extend_days - i1_res)

# Horizontal key level at the overall low of the session
key_support = low.min()

full_days = pd.date_range(dates.min().normalize(), dates.max().normalize(), freq="D")
bar_width = pd.Timedelta(hours=14)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
fig.suptitle("Candlestick with Trader Lines on busday Scale", fontsize=14, fontweight="bold")

ax2.set_xscale("busday")


def _draw(ax):
    # Candles
    ax.vlines(draw_times, low, high, linewidth=0.9, color="black", zorder=3)
    ax.bar(
        draw_times,
        body_height,
        bottom=body_bottom,
        width=bar_width,
        color=colors,
        zorder=4,
    )

    # Support trend line
    ax.plot(
        [draw_times[i1_sup], future_date],
        [y_sup_start, y_sup_end],
        linestyle="--",
        linewidth=1.4,
        color="green",
        alpha=0.85,
        label="Support trend",
    )

    # Resistance trend line
    ax.plot(
        [draw_times[i1_res], future_date],
        [y_res_start, y_res_end],
        linestyle="--",
        linewidth=1.4,
        color="red",
        alpha=0.85,
        label="Resistance trend",
    )

    # Horizontal key support level
    ax.axhline(
        key_support,
        linestyle=":",
        linewidth=1.2,
        color="steelblue",
        alpha=0.8,
        label=f"Key support ({key_support:.2f})",
    )

    # Pivot markers
    ax.scatter(
        [draw_times[i1_sup], draw_times[i2_sup]],
        [low[i1_sup], low[i2_sup]],
        marker="o",
        color="green",
        s=40,
        zorder=5,
    )
    ax.scatter(
        [draw_times[i1_res], draw_times[i2_res]],
        [high[i1_res], high[i2_res]],
        marker="o",
        color="red",
        s=40,
        zorder=5,
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
        ax1.axvspan(d, d + pd.Timedelta(days=2), color="grey", alpha=0.12, linewidth=0)

# --- Business axis ---
_draw(ax2)
ax2.set_title("Business Time (scale='busday')")
ax2.xaxis.set_major_locator(busdayaxis.BusdayLocator(mdates.DayLocator()))
ax2.xaxis.set_major_formatter(mdates.DateFormatter("%a %d %b"))
ax2.tick_params(axis="x", rotation=90)

for d in full_days:
    if d.weekday() == 5:  # Saturday
        ax2.axvline(d, linestyle="--", linewidth=0.8, alpha=0.5)
        ax2.axvline(d + pd.Timedelta(days=2), linestyle="--", linewidth=0.8, alpha=0.5)

plt.tight_layout()
plt.show()

# %%
