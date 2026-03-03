"""
Hourly random walk with zero weekend returns.

Calendar axis:
    - Daily ticks
    - Weekend shading
    - Flat weekend segments

Business axis:
    - Weekends compressed
"""

# %%
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import mplbusdayaxis

mplbusdayaxis.register_scale()

num_days = 20
dates = pd.date_range("2025-01-01", periods=num_days * 24, freq="h")

returns = np.random.normal(0, 0.002, len(dates))
returns[dates.weekday >= 5] = 0.0

prices = 100 * (1 + pd.Series(returns, index=dates)).cumprod()


fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 7), sharey=True)

fig.suptitle(
    "Comparison of Calendar Time vs Business-Day Scale", fontsize=14, fontweight="bold"
)


# --- Calendar axis ---
ax1.plot(dates, prices.values, linewidth=1.3)
ax1.set_title("Calendar Time (scale='linear')")
ax1.set_ylabel("Price")

ax1.xaxis.set_major_locator(mdates.DayLocator())
ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
ax1.tick_params(axis="x", rotation=90)

# Shade weekends
full_days = pd.date_range(dates.min().normalize(), dates.max().normalize(), freq="D")

for d in full_days:
    if d.weekday() == 5:  # Saturday
        ax1.axvspan(d, d + pd.Timedelta(days=2), color="grey", alpha=0.15, linewidth=0)


# --- Business axis ---
ax2.plot(dates, prices.values, linewidth=1.3)
ax2.set_xscale("busday")
ax2.set_title("Business Time (scale='busday')")
ax2.set_ylabel("Price")
ax2.tick_params(axis="x", rotation=90)

# Mark weekend boundaries
for d in full_days:
    if d.weekday() == 5:
        ax2.axvline(d, linestyle="--", linewidth=0.8, alpha=0.6)
        ax2.axvline(d + pd.Timedelta(days=2), linestyle="--", linewidth=0.8, alpha=0.6)


plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.show()

# %%
