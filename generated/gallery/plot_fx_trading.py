"""
Per-Day Business Hours

Calendar axis:
    - Hourly ticks
    - Per-day inactive period shading

Business axis:
    - Each day proportional to its session length
    - Friday (3h) visibly narrower than Mon–Thu (8h)
"""

# %%
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import busdayaxis

busdayaxis.register_scale()

OPEN = 9
CLOSE_REGULAR = 17  # Mon–Thu: 8-hour session
CLOSE_FRIDAY = 12   # Friday: 3-hour session (early close)

bushours = {
    "Mon": (OPEN, CLOSE_REGULAR),
    "Tue": (OPEN, CLOSE_REGULAR),
    "Wed": (OPEN, CLOSE_REGULAR),
    "Thu": (OPEN, CLOSE_REGULAR),
    "Fri": (OPEN, CLOSE_FRIDAY),
}

num_days = 5
dates = pd.date_range("2025-01-06", periods=num_days * 24, freq="h")  # Mon–Fri

returns = np.random.normal(0, 0.002, len(dates))
close_hours = np.where(dates.weekday == 4, CLOSE_FRIDAY, CLOSE_REGULAR)
returns[(dates.hour < OPEN) | (dates.hour >= close_hours)] = 0.0

prices = 100 * (1 + pd.Series(returns, index=dates)).cumprod()

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 7), sharey=True)
fig.suptitle(
    f"Per-Day Sessions: Mon–Thu {OPEN}:00–{CLOSE_REGULAR}:00, Fri {OPEN}:00–{CLOSE_FRIDAY}:00",
    fontsize=13,
    fontweight="bold",
)

full_days = pd.date_range(dates.min().normalize(), dates.max().normalize(), freq="D")

# --- Calendar axis ---
ax1.plot(dates, prices.values, linewidth=1.3)
ax1.set_title("Calendar Time (scale='linear')")
ax1.set_ylabel("Price")
ax1.xaxis.set_major_locator(mdates.HourLocator(byhour=range(OPEN, CLOSE_REGULAR + 1, 2)))
ax1.xaxis.set_major_formatter(mdates.DateFormatter("%a %H:%M"))
ax1.tick_params(axis="x", rotation=90)

# Shade inactive periods per day
for d in full_days:
    close = CLOSE_FRIDAY if d.weekday() == 4 else CLOSE_REGULAR
    ax1.axvspan(d, d + pd.Timedelta(hours=OPEN), color="grey", alpha=0.15, linewidth=0)
    ax1.axvspan(
        d + pd.Timedelta(hours=close),
        d + pd.Timedelta(hours=24),
        color="grey",
        alpha=0.15,
        linewidth=0,
    )

# --- Business axis ---
ax2.plot(dates, prices.values, linewidth=1.3)
ax2.set_xscale("busday", bushours=bushours)
ax2.set_title("Business Time (scale='busday', bushours={per-day})")
ax2.set_ylabel("Price")
ax2.xaxis.set_major_locator(
    busdayaxis.BusdayLocator(mdates.HourLocator(byhour=range(OPEN, CLOSE_REGULAR + 1, 2)))
)
ax2.xaxis.set_major_formatter(mdates.DateFormatter("%a %H:%M"))
ax2.tick_params(axis="x", rotation=90)

# Mark open/close boundaries
for d in full_days:
    close = CLOSE_FRIDAY if d.weekday() == 4 else CLOSE_REGULAR
    ax2.axvline(d + pd.Timedelta(hours=OPEN), linestyle="--", linewidth=0.8, alpha=0.6)
    ax2.axvline(d + pd.Timedelta(hours=close), linestyle="--", linewidth=0.8, alpha=0.6)

plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.show()

# %%
