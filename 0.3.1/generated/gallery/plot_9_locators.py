"""# Locator Showcase

All business-day-aware locators side by side. Each subplot uses the same
intraday data but a different locator, so the tick-placement differences are
immediately visible.

Locators shown (top to bottom):

- ``AutoDateLocator`` — automatic tick spacing
- ``DayLocator`` — one tick per day (midnight)
- ``WeekdayLocator`` — ticks on specific weekdays
- ``HourLocator`` — ticks at specified hours
- ``MinuteLocator`` — ticks at specified minutes
- ``MidBusdayLocator`` — one tick centred in each session
"""

# %%
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import busdayaxis

# %%
# Prepare dummy intraday data (Mon–Fri, 09:00–17:00)
OPEN, CLOSE = 9, 17
num_days = 5
dates = pd.date_range("2025-01-06", periods=num_days * 24 * 60, freq="min")
returns = np.random.normal(0, 0.0002, len(dates))
returns[~np.is_busday(np.array(dates, dtype="datetime64[D]"))] = 0.0
returns[(dates.hour < OPEN) | (dates.hour >= CLOSE)] = 0.0
prices = (1 + pd.Series(returns, index=dates)).cumprod()

# %%
# Build the figure — one subplot per locator
locators = [
    ("AutoDateLocator", busdayaxis.AutoDateLocator()),
    ("DayLocator", busdayaxis.DayLocator()),
    (
        "WeekdayLocator(byweekday=[MO, WE, FR])",
        busdayaxis.WeekdayLocator(byweekday=[0, 2, 4]),
    ),
    ("HourLocator(interval=2)", busdayaxis.HourLocator(interval=2)),
    ("MinuteLocator(byminute=[0, 30])", busdayaxis.MinuteLocator(byminute=[0, 30])),
    ("MidBusdayLocator", busdayaxis.MidBusdayLocator()),
]

fig, axes = plt.subplots(len(locators), 1, figsize=(10, 14), sharey=True)
fig.suptitle("Locator showcase — same data, different tick locators", fontsize=14)

for ax, (label, locator) in zip(axes, locators):
    ax.plot(dates, prices.values, linewidth=1)
    ax.set_xscale("busday", bushours=(OPEN, CLOSE))
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%a %H:%M"))
    ax.tick_params(axis="x", rotation=45, labelsize=8)
    ax.set_title(label, fontsize=10, loc="left")
    busdayaxis.mark_gaps(ax, alpha=0.4)

_ = plt.tight_layout(rect=[0, 0, 1, 0.97])
