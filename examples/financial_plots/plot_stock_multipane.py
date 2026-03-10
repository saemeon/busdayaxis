"""# Multi-Pane Stock Chart"""

# %%
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import busdayaxis

busdayaxis.register_scale()

rng = np.random.default_rng(42)

# Intraday hourly bars for 5 business days, 9:00-17:00
hours = list(range(9, 18))
dates = pd.bdate_range("2025-01-02", periods=5)
times = [d + pd.Timedelta(hours=h) for d in dates for h in hours]
bar_idx = pd.DatetimeIndex(times)

# Generate OHLC with random walk
returns = rng.normal(0, 0.002, len(bar_idx))
close = 100 * (1 + pd.Series(returns, index=bar_idx)).cumprod()
open_ = close.shift(1).fillna(100)
high = np.maximum(open_.values, close.values) + rng.uniform(0.01, 0.15, len(bar_idx))
low = np.minimum(open_.values, close.values) - rng.uniform(0.01, 0.15, len(bar_idx))

# Colors based on close vs open
colors = ["green" if c >= o else "red" for c, o in zip(close.values, open_.values)]
body_bottom = np.minimum(open_.values, close.values)
body_height = np.abs(close.values - open_.values)

# Volume (random, scaled)
volume = rng.integers(1000, 5000, len(bar_idx))

# SMA indicator
sma = close.rolling(window=5).mean()

# Layout: 3 rows, share x-axis
fig = plt.figure(figsize=(10, 8))
gs = fig.add_gridspec(3, 1, height_ratios=[3, 1, 1], hspace=0.05)

ax_price = fig.add_subplot(gs[0])
ax_vol = fig.add_subplot(gs[1], sharex=ax_price)
ax_sma = fig.add_subplot(gs[2], sharex=ax_price)

fig.suptitle("AAPL 5-Day Intraday (busday scale)", fontsize=14)

# --- Price Panel ---
# Draw wicks first (so they appear behind bodies)
ax_price.vlines(bar_idx, low, high, linewidth=0.8, color="black", zorder=3)

# Bollinger Bands (20-period, 2 std)
sma = pd.Series(close)
bb_sma = sma.rolling(20).mean()
bb_std = sma.rolling(20).std()
bb_upper = bb_sma + 2 * bb_std
bb_lower = bb_sma - 2 * bb_std
ax_price.plot(bar_idx, bb_sma.values, color="blue", linewidth=1.2)
ax_price.plot(bar_idx, bb_upper.values, color="red", linewidth=1, linestyle="--")
ax_price.plot(bar_idx, bb_lower.values, color="green", linewidth=1, linestyle="--")
ax_price.fill_between(
    bar_idx, bb_lower.values, bb_upper.values, alpha=0.1, color="blue"
)
ax_price.bar(
    bar_idx,
    body_height,
    bottom=body_bottom,
    width=pd.Timedelta(minutes=55),
    color=colors,
    zorder=4,
)
ax_sma.plot(bar_idx, sma.values, color="blue", linewidth=1.2, label="SMA(5)")
ax_price.set_ylabel("Price")
ax_price.tick_params(axis="x", labelbottom=False)
ax_vol.bar(bar_idx, volume, color=colors, alpha=0.6, width=pd.Timedelta(minutes=55))
ax_vol.set_ylabel("Volume", fontsize=9)
ax_vol.tick_params(axis="x", labelbottom=False)
ax_sma.plot(bar_idx, sma.values, color="blue", linewidth=1.2)
ax_sma.set_ylabel("SMA(5)", fontsize=9)

for ax in [ax_price, ax_vol, ax_sma]:
    ax.xaxis.set_major_locator(busdayaxis.HourLocator(byhour=range(9, 18, 2)))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%a %H:%M"))

for ax in [ax_price, ax_vol, ax_sma]:
    ax.set_xscale("busday", bushours=(9, 17))

_ = ax_sma.tick_params(axis="x", rotation=45)
