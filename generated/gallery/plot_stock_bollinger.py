"""# Financial Chart with Bollinger Bands

Price chart with Bollinger Bands (20-period SMA ± 2 standard deviations).
Bands expand during high volatility and contract during low volatility.

Core code:

```python
ax.set_xscale("busday", bushours=(9, 17))
```

Panels:

- **Price**: Candlesticks + SMA(20) + Upper/Lower Bollinger Bands
"""

# %%
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import busdayaxis

busdayaxis.register_scale()

rng = np.random.default_rng(42)
n = 100
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

# Price data with varying volatility
vol_base = np.linspace(0.003, 0.008, n)  # increasing volatility
returns = rng.normal(0.0005, vol_base)
trend = np.linspace(0, 0.08, n)
close = 100 * (1 + trend + pd.Series(returns).cumsum()).values

# OHLC
open_ = np.roll(close, 1)
open_[0] = close[0]
high = np.maximum(open_, close) + rng.uniform(0.05, 0.2, n)
low = np.minimum(open_, close) - rng.uniform(0.05, 0.2, n)

colors = ["green" if c >= o else "red" for c, o in zip(close, open_)]
body_bottom = np.minimum(open_, close)
body_height = np.abs(close - open_)

# Bollinger Bands (20-period, 2 std)
sma = pd.Series(close)
bb_sma = sma.rolling(20).mean()
bb_std = sma.rolling(20).std()
bb_upper = bb_sma + 2 * bb_std
bb_lower = bb_sma - 2 * bb_std

# Plot
fig, ax = plt.subplots(figsize=(12, 6))

bar_width = pd.Timedelta(minutes=55)

# Wicks
ax.vlines(bar_idx, low, high, linewidth=0.6, color="black", zorder=3)
# Bodies
ax.bar(
    bar_idx, body_height, bottom=body_bottom, width=bar_width, color=colors, zorder=4
)

# Bollinger Bands
ax.plot(bar_idx, bb_sma.values, color="blue", linewidth=1.2, label="SMA(20)")
ax.plot(
    bar_idx, bb_upper.values, color="red", linewidth=1, linestyle="--", label="BB Upper"
)
ax.plot(
    bar_idx,
    bb_lower.values,
    color="green",
    linewidth=1,
    linestyle="--",
    label="BB Lower",
)
ax.fill_between(bar_idx, bb_lower.values, bb_upper.values, alpha=0.1, color="blue")

ax.set_ylabel("Price")
ax.legend(loc="upper left", fontsize=9)
ax.set_title("Bollinger Bands (20, 2)", fontsize=14, fontweight="bold")

# Set locators BEFORE scale to avoid AutoDateLocator generating too many ticks
hour_locator = busdayaxis.BusdayLocator(mdates.HourLocator(byhour=range(9, 17, 2)))
ax.xaxis.set_major_locator(hour_locator)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))

# Apply busday scale
ax.set_xscale("busday", bushours=(9, 17))

ax.tick_params(axis="x", rotation=45)

plt.tight_layout()
plt.show()

# %%
