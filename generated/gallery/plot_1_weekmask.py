"""# Custom Work Week

A ``weekmask`` string defines which days are business days.
The string must be compatible with ``np.is_busday``.

This example uses the Middle-Eastern Sun–Thu work week; Friday and Saturday
are collapsed, while Sunday is treated as a normal business day.

Core code:

```python
ax.set_xscale("busday", weekmask="Sun Mon Tue Wed Thu")
```
"""

# %%
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import busdayaxis

busdayaxis.register_scale()

WEEKMASK = "Sun Mon Tue Wed Thu"  # Middle-Eastern work week

# define dummy data
num_days = 6
dates = pd.date_range("2025-01-08", periods=num_days * 24, freq="h")  # starts Sunday
returns = np.random.normal(0, 0.002, len(dates))
returns[~np.is_busday(np.array(dates, dtype="datetime64[D]"), weekmask=WEEKMASK)] = 0.0
prices = (1 + pd.Series(returns, index=dates)).cumprod()


fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 7), sharey=True)
fig.suptitle(f"Custom Work Week (weekmask='{WEEKMASK}')", fontsize=14)

# axis with default linear scale
ax1.plot(dates, prices.values, linewidth=1.3)
ax1.set_title("Calendar Time (scale='linear')")
ax1.set_ylabel("Price")
ax1.xaxis.set_major_locator(mdates.DayLocator())
ax1.xaxis.set_major_formatter(mdates.DateFormatter("%a %-d"))

# axis with business scale
ax2.plot(dates, prices.values, linewidth=1.3)
ax2.set_xscale("busday", weekmask=WEEKMASK)
ax2.set_title(f"Business Time (scale='busday', weekmask='{WEEKMASK}')")
ax2.set_ylabel("Price")
ax2.xaxis.set_major_locator(busdayaxis.DayLocator())
ax2.xaxis.set_major_formatter(mdates.DateFormatter("%a %-d"))

# Shade Fri–Sat (Middle-Eastern weekend)
full_days = pd.date_range(dates.min().normalize(), dates.max().normalize(), freq="D")
for d in full_days:
    if d.weekday() == 4:  # Friday
        ax1.axvspan(d, d + pd.Timedelta(days=2), color="grey", alpha=0.15, linewidth=0)
# Mark Fri–Sat boundaries
for d in full_days:
    if d.weekday() == 4:  # Friday
        ax2.axvline(d, linestyle="--", linewidth=0.8, alpha=0.6)
        ax2.axvline(d + pd.Timedelta(days=2), linestyle="--", linewidth=0.8, alpha=0.6)

_ = plt.tight_layout(rect=[0, 0, 1, 0.96])
