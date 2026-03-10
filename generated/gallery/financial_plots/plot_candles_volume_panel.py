"""# Candlestick Chart with Separate Volume Panel"""

# %%
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import busdayaxis

busdayaxis.register_scale()

rng = np.random.default_rng(42)

# Daily OHLC data — business days only, centered at noon to avoid weekend edges
dates = pd.bdate_range("2025-01-01", periods=14)
draw_times = dates + pd.Timedelta(hours=12)

returns = rng.normal(0, 0.01, len(dates))
close = 100 * (1 + pd.Series(returns, index=dates)).cumprod()
open_ = close.shift(1).fillna(100)
high = np.maximum(open_.values, close.values) + rng.uniform(0.1, 0.8, len(dates))
low = np.minimum(open_.values, close.values) - rng.uniform(0.1, 0.8, len(dates))

colors = ["green" if c >= o else "red" for c, o in zip(close.values, open_.values)]
body_bottom = np.minimum(open_.values, close.values)
body_height = np.abs(close.values - open_.values)

volume = rng.integers(1_000, 10_000, len(dates))

full_days = pd.date_range(dates.min().normalize(), dates.max().normalize(), freq="D")
bar_width = pd.Timedelta(hours=14)

fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(
    2, 2, figsize=(10, 6), gridspec_kw={"height_ratios": [3, 1]}
)
fig.suptitle("Candlestick Chart — Daily", fontsize=14)


def _draw(ax_price, ax_vol):
    ax_price.vlines(
        draw_times, low, high, linewidth=1, color="black", zorder=3
    )  # problem here
    ax_price.bar(
        draw_times,
        body_height,
        bottom=body_bottom,
        width=bar_width,
        color=colors,
        zorder=4,
    )
    ax_price.set_ylabel("Price")

    ax_vol.bar(draw_times, volume, color=colors, alpha=0.6, width=bar_width)
    ax_vol.set_ylabel("Volume", fontsize=8)
    ax_vol.tick_params(axis="y", labelsize=7)


# --- Calendar axes ---
_draw(ax1, ax3)
ax1.set_title("Calendar Time (scale='linear')")
ax1.xaxis.set_major_locator(mdates.DayLocator())
ax1.xaxis.set_major_formatter(mdates.DateFormatter("%a %d %b"))
ax1.tick_params(axis="x", rotation=90, labelbottom=False)
ax3.xaxis.set_major_locator(mdates.DayLocator())
ax3.xaxis.set_major_formatter(mdates.DateFormatter("%a %d %b"))
ax3.tick_params(axis="x", rotation=90)

for d in full_days:
    if d.weekday() == 5:  # Saturday
        ax1.axvspan(d, d + pd.Timedelta(days=2), color="grey", alpha=0.15, linewidth=0)
        ax3.axvspan(d, d + pd.Timedelta(days=2), color="grey", alpha=0.15, linewidth=0)

# --- Business axes ---
_draw(ax2, ax4)
ax2.set_title("Business Time (scale='busday')")
ax2.tick_params(axis="x", rotation=90, labelbottom=False)
ax4.tick_params(axis="x", rotation=90)

# Set busday scale AFTER plotting to establish correct axis limits
ax2.xaxis.set_major_locator(busdayaxis.DayLocator())
ax2.xaxis.set_major_formatter(mdates.DateFormatter("%a %d %b"))
ax4.xaxis.set_major_locator(busdayaxis.DayLocator())
ax4.xaxis.set_major_formatter(mdates.DateFormatter("%a %d %b"))
ax2.set_xscale("busday")
ax4.set_xscale("busday")

for d in full_days:
    if d.weekday() == 5:  # Saturday
        ax2.axvline(d, linestyle="--", linewidth=0.8, alpha=0.6)
        ax2.axvline(d + pd.Timedelta(days=2), linestyle="--", linewidth=0.8, alpha=0.6)
        ax4.axvline(d, linestyle="--", linewidth=0.8, alpha=0.6)
        ax4.axvline(d + pd.Timedelta(days=2), linestyle="--", linewidth=0.8, alpha=0.6)

_ = plt.tight_layout(rect=[0, 0, 1, 0.96])
