"""# Multiple Artists

All standard Matplotlib artists work transparently on the busday scale.
Volume bars use ``twinx`` with the same busday scale applied to the
secondary axis.

Core code:

```python
ax.set_xscale("busday")
ax_vol = ax.twinx()
ax_vol.set_xscale("busday")  # twin must match parent
```
"""

# %%
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import busdayaxis

busdayaxis.register_scale()

num_days = 20
dates = pd.date_range("2025-01-01", periods=num_days * 24, freq="h")

returns = np.random.normal(0, 0.002, len(dates))
returns[dates.weekday >= 5] = 0.0

prices = 100 * (1 + pd.Series(returns, index=dates)).cumprod()

# End-of-day snapshots at 16:00 on each weekday
eod = prices[(dates.hour == 16) & (dates.weekday < 5)]

# Synthetic daily high/low for vlines
rng = np.random.default_rng(0)
eod_high = eod + rng.uniform(0.1, 0.6, len(eod))
eod_low = eod - rng.uniform(0.1, 0.6, len(eod))

# Random volume
volume = pd.Series(rng.integers(1_000, 10_000, len(eod)), index=eod.index)

price_min = prices.values.min()

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 7), sharey=True)
fig.suptitle("Multiple Artists on busday Scale", fontsize=14, fontweight="bold")

# Twin axes for volume bars (secondary y-axis)
ax1_vol = ax1.twinx()
ax2_vol = ax2.twinx()

full_days = pd.date_range(dates.min().normalize(), dates.max().normalize(), freq="D")


def _draw(ax, ax_vol, *, busday: bool):
    # Volume bars (drawn first so price renders on top)
    ax_vol.bar(volume.index, volume.values, width=0.8, alpha=0.25, color="green")
    ax_vol.set_ylabel("Volume", color="green", fontsize=8)
    ax_vol.tick_params(axis="y", labelcolor="green", labelsize=7)
    if busday:
        ax_vol.set_xscale("busday")

    # Price artists
    ax.fill_between(dates, prices.values, price_min, alpha=0.12)
    ax.plot(dates, prices.values, linewidth=1.3)
    ax.step(
        eod.index,
        eod.values,
        where="post",
        linewidth=0.9,
        linestyle="--",
        color="orange",
        alpha=0.8,
        label="Daily close (step)",
    )
    ax.scatter(eod.index, eod.values, s=25, zorder=5, label="End-of-Day (scatter)")

    ax.axhline(
        100,
        linestyle=":",
        linewidth=1.0,
        color="black",
        alpha=0.5,
        label="Initial price (axhline)",
    )

    ax.set_ylabel("Price")
    ax.legend(fontsize=7, loc="upper left")
    ax.set_zorder(ax_vol.get_zorder() + 1)
    ax.patch.set_visible(False)


# --- Calendar axis ---
_draw(ax1, ax1_vol, busday=False)
ax1.set_title("Calendar Time (scale='linear')")
ax1.xaxis.set_major_locator(mdates.DayLocator())
ax1.xaxis.set_major_formatter(mdates.DateFormatter("%a %d %b"))
ax1.tick_params(axis="x", rotation=90)

for d in full_days:
    if d.weekday() == 5:
        ax1.axvspan(d, d + pd.Timedelta(days=2), color="grey", alpha=0.15, linewidth=0)

# --- Business axis ---
_draw(ax2, ax2_vol, busday=True)
ax2.set_xscale("busday")
ax2.set_title("Business Time (scale='busday')")
ax2.xaxis.set_major_locator(busdayaxis.BusdayLocator(mdates.DayLocator()))
ax2.xaxis.set_major_formatter(mdates.DateFormatter("%a %d %b"))
ax2.tick_params(axis="x", rotation=90)

for d in full_days:
    if d.weekday() == 5:
        ax2.axvline(d, linestyle="--", linewidth=0.8, alpha=0.6)
        ax2.axvline(d + pd.Timedelta(days=2), linestyle="--", linewidth=0.8, alpha=0.6)

plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.show()

# %%
