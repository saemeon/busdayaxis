"""
Business Day Scale Example
==========================

This example demonstrates how to use the business day scale in matplotlib.
"""

# %%
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import busdayaxis

busdayaxis.register_scale()

dates = pd.date_range("2026-01-01", periods=25, freq="D")
values = range(len(dates))


# %%
# Linear Scale Example
fig, ax = plt.subplots()

ax.plot(dates, values)
ax.set_xscale("linear")
ax.tick_params(axis="x", rotation=90)

plt.show()

# %%
# Business Day Scale Example
fig, ax = plt.subplots()

ax.plot(dates, values)
ax.set_xscale("busday")
ax.tick_params(axis="x", rotation=90)

plt.show()

# %%
# Business Day Scale Example
fig, ax = plt.subplots()

ax.plot(dates, values)
ax.set_xscale(busdayaxis.BusdayScale(ax))
ax.tick_params(axis="x", rotation=90)

plt.show()

# %%
# Business Day Scale Example with holidays
fig, ax = plt.subplots()

ax.plot(dates, values)
ax.set_xscale(busdayaxis.BusdayScale(ax, holidays=["2026-01-01", "2026-01-08"]))
ax.tick_params(axis="x", rotation=90)
plt.show()

# %%
# Business Day Scale Example with holidays
fig, ax = plt.subplots()

ax.plot(dates, values)
ax.set_xscale("busday", holidays=["2026-01-01", "2026-01-08"])
ax.tick_params(axis="x", rotation=90)
plt.show()


# %%
# Comparison of linear time scale and business-day scale with business hours

# Example data restricted to business hours
bushours = (9, 16)
dates = pd.date_range("2026-01-05 00:00", periods=100, freq="h")
dates = dates.where(dates.hour >= bushours[0], pd.NaT)
dates = dates.where(dates.hour <= bushours[1], pd.NaT)
dates = dates.dropna()

values = [i + np.random.randint(0, 10) for i in range(len(dates))]

fig, (ax_linear, ax_busday) = plt.subplots(2, 1, sharex=False, figsize=(10, 6))

# Linear scale
ax_linear.plot(dates, values, marker="*")
ax_linear.set_title("Linear time scale")
ax_linear.set_xscale("linear")
ax_linear.xaxis.set_major_locator(mdates.HourLocator(interval=1))
ax_linear.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M"))
ax_linear.tick_params(axis="x", rotation=90)

# Business-day scale with business hours
ax_busday.plot(dates, values, marker="*")
ax_busday.set_title(f"Business-day scale ({bushours[0]}:00–{bushours[1]}:00)")
ax_busday.set_xscale("busday", bushours=bushours)
ax_busday.xaxis.set_major_locator(
    busdayaxis.BusdayLocator(base_locator=mdates.HourLocator(interval=1))
)
ax_busday.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M"))
ax_busday.tick_params(axis="x", rotation=90)

plt.tight_layout()
plt.show()
# %%
# Comparison of linear time scale and business-day scale with business hours

# Example data restricted to business hours
bushours = (9, 16)
dates = pd.date_range("2026-01-05 00:00", periods=85, freq="h")
dates = dates.where(dates.hour >= bushours[0], pd.NaT)
dates = dates.where(dates.hour <= bushours[1], pd.NaT)
dates = dates.dropna()

values = [i + np.random.randint(0, 10) for i in range(len(dates))]

fig, (ax_linear, ax_busday) = plt.subplots(2, 1, sharex=False, figsize=(10, 6))

# Linear scale
ax_linear.plot(dates, values, marker="*")
ax_linear.set_title("Linear time scale")


ax_linear.tick_params(axis="x", rotation=90)

# Business-day scale with business hours
ax_busday.plot(dates, values, marker="*")
ax_busday.set_title(f"Business-day scale ({bushours[0]}:00–{bushours[1]}:00)")
ax_busday.set_xscale("busday", bushours=bushours)
ax_busday.tick_params(axis="x", rotation=90)

plt.tight_layout()
plt.show()
