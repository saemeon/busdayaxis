"""
Business Hours: Compressing Overnight Gaps
===========================================

When plotting intraday data the x-axis normally shows large blank stretches
overnight and over weekends.  The ``busday`` scale's ``bushours`` parameter
collapses those gaps so every tick corresponds to an active trading minute.
"""

# %%
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import busdayaxis

busdayaxis.register_scale()

rng = np.random.default_rng(1)

# One full week of hourly data (Mon–Fri, 24 h/day)
dates = pd.date_range("2026-01-05 00:00", periods=5 * 24 * 60, freq="min")


returns = rng.normal(0, 0.002, len(dates))
returns[dates.weekday >= 5] = 0.0
returns[(dates.hour < 9) | (dates.hour >= 17)] = 0.0
prices = 100 * (1 + pd.Series(returns, index=dates)).cumprod()

OPEN, CLOSE = 9, 17  # active session hours

all_days = pd.date_range(dates[0].normalize(), dates[-1].normalize(), freq="D")

# %%
# Calendar vs. Business Hours
# ----------------------------
# The left panel shows the raw calendar axis with large gaps overnight.
# The right panel uses ``bushours=(9, 17)`` to collapse those gaps.

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharey=True)
fig.suptitle("Overnight gaps: calendar time vs. business hours", fontweight="bold")

# --- Calendar axis ---
ax1.plot(dates, prices.values, linewidth=1.3)
ax1.set_title("Calendar time  (scale='linear')")
ax1.set_ylabel("Price")
ax1.xaxis.set_major_locator(mdates.HourLocator(byhour=[0, 9, 17]))
ax1.xaxis.set_major_formatter(mdates.DateFormatter("%a %H:%M"))
ax1.tick_params(axis="x", rotation=90)

# Shade overnight gaps (before open and after close) and full weekend days
for d in all_days:
    if d.weekday() < 5:
        ax1.axvspan(
            d, d + pd.Timedelta(hours=OPEN), color="grey", alpha=0.12, linewidth=0
        )
        ax1.axvspan(
            d + pd.Timedelta(hours=CLOSE),
            d + pd.Timedelta(days=1),
            color="grey",
            alpha=0.12,
            linewidth=0,
        )
    else:
        ax1.axvspan(d, d + pd.Timedelta(days=1), color="grey", alpha=0.12, linewidth=0)

# --- Business-hours axis ---
ax2.plot(dates, prices.values, linewidth=1.3)
ax2.set_title(f"Business time  (bushours=({OPEN}, {CLOSE}))")
ax2.set_ylabel("Price")
ax2.set_xscale("busday", bushours=(OPEN, CLOSE))
ax2.xaxis.set_major_locator(
    busdayaxis.BusdayLocator(mdates.HourLocator(byhour=range(OPEN, CLOSE + 1)))
)
ax2.xaxis.set_major_formatter(mdates.DateFormatter("%a %H:%M"))
ax2.tick_params(axis="x", rotation=90)

# Mark session open/close boundaries (the cut-out regions)
for d in all_days:
    if d.weekday() < 5:
        ax2.axvline(
            d + pd.Timedelta(hours=OPEN),
            color="steelblue",
            alpha=0.4,
            linewidth=0.8,
            linestyle="--",
        )
        ax2.axvline(
            d + pd.Timedelta(hours=CLOSE),
            color="steelblue",
            alpha=0.4,
            linewidth=0.8,
            linestyle="--",
        )

plt.tight_layout(rect=[0, 0, 1, 0.95])
plt.show()


# %%
# Three ways to specify bushours
# --------------------------------
# The ``bushours`` parameter accepts a tuple, a list of 7 tuples, or a dict.
# All three forms below encode the same schedule: Mon–Thu 9–17, Fri 9–16.

per_day = [
    (9, 17),  # Mon
    (9, 17),  # Tue
    (9, 17),  # Wed
    (9, 17),  # Thu
    (9, 16),  # Fri — early close
    (0, 0),  # Sat — closed
    (0, 0),  # Sun — closed
]

hours_dict = {
    "Mon": (9, 17),
    "Tue": (9, 17),
    "Wed": (9, 17),
    "Thu": (9, 17),
    "Fri": (9, 16),  # early close; Sat/Sun omitted → default (0, 24)
}

fig, axes = plt.subplots(3, 1, figsize=(10, 9), sharey=True)
fig.suptitle("Three ways to specify bushours", fontweight="bold")

specs = [
    (axes[0], (9, 17), "tuple  (9, 17) — uniform session every day"),
    (axes[1], per_day, "list of 7 tuples — Friday closes at 16:00"),
    (axes[2], hours_dict, "dict with string keys — same schedule, Friday 16:00"),
]

for ax, bushours, label in specs:
    ax.plot(dates, prices.values, linewidth=1.3)
    ax.set_xscale("busday", bushours=bushours)
    ax.set_title(f"bushours={label}")
    ax.set_ylabel("Price")
    ax.xaxis.set_major_locator(
        busdayaxis.BusdayLocator(mdates.HourLocator(byhour=range(9, 18)))
    )
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%a %H:%M"))
    ax.tick_params(axis="x", rotation=90)
    # Mark day boundaries (session cut-out regions)
    for d in all_days:
        if d.weekday() < 5:
            ax.axvline(d, color="steelblue", alpha=0.3, linewidth=0.8, linestyle="--")

plt.tight_layout(rect=[0, 0, 1, 0.98])

plt.show()
