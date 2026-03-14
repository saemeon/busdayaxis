"""# Under the Hood

Matplotlib represents dates as floats — days since 1970-01-01. `busdayaxis`
applies the same idea but counts only active time: the internal value is
cumulative business hours divided by 24, so each unit still corresponds to one
full day's worth of open-market time.

Core code:

```python
ax.set_xscale("busday", bushours=(9, 17))
```
"""

# %%
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

import busdayaxis

busdayaxis.register_scale()

# define dummy data
OPEN = 9
CLOSE = 17
num_days = 7
dates = pd.date_range("1969-12-31", periods=num_days * 24, freq="h")
returns = np.random.normal(0, 0.002, len(dates))
returns[~np.is_busday(np.array(dates, dtype="datetime64[D]"))] = 0.0
returns[(dates.hour <= OPEN) | (dates.hour > CLOSE)] = 0.0
prices = (1 + pd.Series(returns, index=dates)).cumprod()

# Plot for README
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8, 4))
fig.suptitle("default vs. ax.set_xscale('busday', bushours=(9, 17))")

# axis with default linear scale
ax1.plot(dates, prices.values, linewidth=1.3)
ax1.xaxis.set_major_locator(mdates.DayLocator())
ax1.xaxis.set_major_formatter(mdates.DateFormatter("%a %Y-%m-%d"))
ax1.tick_params(axis="x", rotation=90)
ax1.set_xlabel("date")

# axis with business scale
ax2.plot(dates, prices.values, linewidth=1.3)
ax2.set_xscale("busday", bushours=(9, 17))
ax2.xaxis.set_major_locator(busdayaxis.DayLocator())
ax2.xaxis.set_major_formatter(mdates.DateFormatter("%a %Y-%m-%d"))
ax2.tick_params(axis="x", rotation=90)
ax2.set_xlabel("date")


# Shade weekends on linear scale
full_days = pd.date_range(dates.min().normalize(), dates.max().normalize(), freq="D")
for d in full_days:
    if d.weekday() == 5:  # Saturday
        ax1.axvspan(d, d + pd.Timedelta(days=2), color="grey", alpha=0.15, linewidth=0)
# Mark weekend boundaries on business scale
for d in full_days:
    if d.weekday() == 5:
        ax2.axvline(d, linestyle="--", linewidth=0.8, alpha=0.6)
        ax2.axvline(d + pd.Timedelta(days=2), linestyle="--", linewidth=0.8, alpha=0.6)


# secondary x-axis showing raw matplotlib float values
ax1_top = ax1.secondary_xaxis("top")
ax1_top.xaxis.set_major_locator(mdates.DayLocator())
ax1_top.xaxis.set_major_formatter(
    mticker.FuncFormatter(
        lambda x, _: f"{ax1.xaxis._scale.get_transform().transform(np.asarray(x)):.2f}"
    )
)
ax1_top.set_xlabel("matplotlib internal: \n days since 1970", labelpad=8)
ax1_top.tick_params(axis="x", rotation=45)


# secondary x-axis showing raw busday float values
ax2_top = ax2.secondary_xaxis("top")
ax2_top.set_xscale("busday", bushours=(9, 17))
ax2_top.xaxis.set_major_locator(busdayaxis.DayLocator())
ax2_top.xaxis.set_major_formatter(
    mticker.FuncFormatter(
        lambda x, _: f"{ax2.xaxis._scale.get_transform().transform(np.asarray(x)):.2f}"
    )
)
ax2_top.set_xlabel(
    "busdayaxis internal (8 business hours per day): \n(business hours since 1970)/24",
    labelpad=8,
)
ax2_top.tick_params(axis="x", rotation=45)


plt.tight_layout(rect=[0, 0, 1, 1])
_ = plt.savefig("under_the_hood.png", dpi=300)
