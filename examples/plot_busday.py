# %%
import matplotlib.pyplot as plt
import pandas as pd

import mplbusdayaxis as bda

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
ax.set_xscale(bda.BusdayScale(ax))
ax.tick_params(axis="x", rotation=90)

plt.show()

# %%
# Business Day Scale Example with holidays
fig, ax = plt.subplots()

ax.plot(dates, values)
ax.set_xscale(bda.BusdayScale(ax, holidays=["2026-01-01", "2026-01-08"]))
ax.tick_params(axis="x", rotation=90)
plt.show()

# %%
# Business Day Scale Example with holidays
fig, ax = plt.subplots()

ax.plot(dates, values)
ax.set_xscale("busday", holidays=["2026-01-01", "2026-01-08"])
ax.tick_params(axis="x", rotation=90)
plt.show()
