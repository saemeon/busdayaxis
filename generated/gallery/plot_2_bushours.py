"""# Uniform Business Hours For All Busdays

If the business of interest is only active during the same hours each day, such as with
overnight gaps and pre/post-market time, pass a ``bushours`` tuple to collapse all
off-hours.

- All weekdays use the same bushours.
- The standard Mon–Fri weekmask still applies so weekends remain collapsed.
- Boundaries accept numeric hours, ISO time strings, or ``datetime.time`` objects —
  the following are all equivalent:

```python
bushours=(9, 17)
bushours=("09:00", "17:00")
bushours=(datetime.time(9), datetime.time(17))
```

Core code:

```python
ax.set_xscale("busday", bushours=(9, 17))
```
"""

# %%
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import busdayaxis

busdayaxis.register_scale()

# define dummy data
OPEN = 9
CLOSE = 17
num_days = 3
dates = pd.date_range("2025-01-06", periods=num_days * 24, freq="h")
returns = np.random.normal(0, 0.002, len(dates))
returns[~np.is_busday(np.array(dates, dtype="datetime64[D]"))] = 0.0
returns[(dates.hour <= OPEN) | (dates.hour > CLOSE)] = 0.0
prices = (1 + pd.Series(returns, index=dates)).cumprod()


fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 7), sharey=True)
fig.suptitle(f"Business Hours ({OPEN}:00–{CLOSE}:00)", fontsize=14)

# axis with default linear scale
ax1.plot(dates, prices.values, linewidth=1.3)
ax1.set_title("default linear matplotlib scale")
ax1.set_ylabel("Price")
ax1.xaxis.set_major_locator(mdates.HourLocator())
ax1.xaxis.set_major_formatter(mdates.DateFormatter("%a %H"))
ax1.tick_params(axis="x", rotation=90)


# axis with business scale
ax2.plot(dates, prices.values, linewidth=1.3)
ax2.set_title(f"using `.set_xscale(('busday', bushours=({OPEN}, {CLOSE}))`")
ax2.set_ylabel("Price")
ax2.tick_params(axis="x", rotation=90)
ax2.set_xscale("busday", bushours=(OPEN, CLOSE))
ax2.xaxis.set_major_locator(busdayaxis.HourLocator())
ax2.xaxis.set_major_formatter(mdates.DateFormatter("%a %H"))

# Shade pre/post-market
full_days = pd.date_range(dates.min().normalize(), dates.max().normalize(), freq="D")
for d in full_days:
    ax1.axvspan(d, d + pd.Timedelta(hours=OPEN), color="grey", alpha=0.15, linewidth=0)
    ax1.axvspan(
        d + pd.Timedelta(hours=CLOSE),
        d + pd.Timedelta(hours=24),
        color="grey",
        alpha=0.15,
        linewidth=0,
    )
# Mark open/close boundaries
for d in full_days:
    ax2.axvline(d + pd.Timedelta(hours=OPEN), linestyle="--", linewidth=0.8, alpha=0.6)
    ax2.axvline(d + pd.Timedelta(hours=CLOSE), linestyle="--", linewidth=0.8, alpha=0.6)

_ = plt.tight_layout(rect=[0, 0, 1, 0.96])
