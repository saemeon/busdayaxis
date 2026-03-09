"""# Financial Chart with RSI Indicator

A price chart with Relative Strength Index (RSI) in a separate panel.
RSI shows overbought (>70) and oversold (<30) conditions.

Core code:

```python
ax_price.set_xscale("busday", bushours=(9, 17))
ax_rsi.set_xscale("busday", bushours=(9, 17))
```

Panels:

- **Price**: Candlesticks + SMA(20)
- **RSI**: 14-period RSI with overbought/oversold zones
"""

# %%
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import busdayaxis

busdayaxis.register_scale()

rng = np.random.default_rng(42)
n = 40

# Generate hourly data
hours = list(range(9, 17))
all_times = []
current = pd.Timestamp("2025-01-06")
while len(all_times) < n:
    if current.weekday() < 5:
        for h in hours:
            all_times.append(current + pd.Timedelta(hours=h))
    current += pd.Timedelta(days=1)

bar_idx = pd.DatetimeIndex(all_times[:n])

# Price data
returns = rng.normal(0.0005, 0.005, n)
trend = np.linspace(0, 0.08, n)
close = 100 * (1 + trend + pd.Series(returns).cumsum()).values

# OHLC
open_ = np.roll(close, 1)
open_[0] = close[0]
high = np.maximum(open_, close) + rng.uniform(0.05, 0.15, n)
low = np.minimum(open_, close) - rng.uniform(0.05, 0.15, n)

colors = ["green" if c >= o else "red" for c, o in zip(close, open_)]
body_bottom = np.minimum(open_, close)
body_height = np.abs(close - open_)

# RSI (14-period)
delta = pd.Series(close).diff()
gain = delta.where(delta > 0, 0).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
rs = gain / loss
rsi = 100 - (100 / (1 + rs))
rsi_values = rsi.values

# SMA(20)
sma20 = pd.Series(close).rolling(20).mean().values

# Layout
fig = plt.figure(figsize=(12, 8))
gs = fig.add_gridspec(2, 1, height_ratios=[3, 1], hspace=0.05)

ax_price = fig.add_subplot(gs[0])
ax_rsi = fig.add_subplot(gs[1], sharex=ax_price)

fig.suptitle("AAPL Intraday with RSI", fontsize=14, fontweight="bold")

bar_width = pd.Timedelta(minutes=55)

# --- Price Panel ---
ax_price.vlines(bar_idx, low, high, linewidth=0.6, color="black", zorder=3)
ax_price.bar(
    bar_idx, body_height, bottom=body_bottom, width=bar_width, color=colors, zorder=4
)
ax_price.plot(bar_idx, sma20, color="blue", linewidth=1.2, label="SMA(20)")

ax_price.set_ylabel("Price")
ax_price.legend(loc="upper left", fontsize=9)

# --- RSI Panel ---
ax_rsi.plot(bar_idx, rsi_values, color="purple", linewidth=1)
ax_rsi.axhline(70, color="red", linestyle="--", linewidth=0.8, alpha=0.7)
ax_rsi.axhline(30, color="green", linestyle="--", linewidth=0.8, alpha=0.7)
ax_rsi.axhline(50, color="gray", linewidth=0.5, alpha=0.5)

# Shade overbought/oversold zones
ax_rsi.fill_between(bar_idx, 70, 100, alpha=0.1, color="red")
ax_rsi.fill_between(bar_idx, 0, 30, alpha=0.1, color="green")

ax_rsi.set_ylabel("RSI")
ax_rsi.set_ylim(0, 100)

# Hide x-axis labels on top panel
ax_price.tick_params(axis="x", labelbottom=False)

# Set locators BEFORE scale to avoid AutoDateLocator generating too many ticks
ax_rsi.xaxis.set_major_locator(busdayaxis.HourLocator(byhour=range(9, 17, 2)))
ax_rsi.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))

# --- Apply busday scale ---
for ax in [ax_price, ax_rsi]:
    ax.set_xscale("busday", bushours=(9, 17))

ax_rsi.tick_params(axis="x", rotation=45)

plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.show()
