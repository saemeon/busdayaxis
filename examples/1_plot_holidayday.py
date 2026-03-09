"""# Exclude Extra Days or Holidays

Pass an array of dates as ``holidays`` keyword argument, compatible with ``np.is_busday()``, to collapsed them on the business axis.

Core code:
```python
ax.set_xscale("busday", holidays=["2025-01-06"])
```
"""

# %%
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import busdayaxis

busdayaxis.register_scale()

saturday = "2025-01-04"
sunday = "2025-01-05"
holiday = "2025-01-06"

num_days = 10

dates = pd.date_range("2025-01-01", periods=num_days * 24, freq="h").to_numpy()
returns = [
    np.random.normal(0, 0.002)
    if np.is_busday(np.datetime64(d, "D"), holidays=[holiday])
    else 0
    for d in dates
]
prices = (1 + pd.Series(returns, index=dates)).cumprod()

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(6.5, 4.5), sharey=True)
fig.suptitle("Exclude Extra Days or Holidays", fontsize=14, fontweight="bold")

# Calendar axis
ax1.plot(dates, prices.values)
ax1.set_title("default linear matplotlib scale")
ax1.xaxis.set_major_locator(mdates.DayLocator())
ax1.xaxis.set_major_formatter(mdates.DateFormatter("%a %-d"))
# Business axis
ax2.plot(dates, prices.values)
ax2.set_xscale("busday", holidays=[holiday])
ax2.set_title(f"using  `ax.set_xscale(scale='busday', holidays=['{holiday}'])`")
ax2.xaxis.set_major_locator(busdayaxis.DayLocator())
ax2.xaxis.set_major_formatter(mdates.DateFormatter("%a %-d"))


# Shade weekend and holiday
for ax in [ax1, ax2]:
    ax.axvspan(
        pd.Timestamp(saturday),
        pd.Timestamp(saturday) + pd.Timedelta(days=2),
        color="grey",
        alpha=0.15,
        linewidth=0,
    )
    ax.axvspan(
        pd.Timestamp(holiday),
        pd.Timestamp(holiday) + pd.Timedelta(days=1),
        color="tomato",
        alpha=0.3,
        linewidth=0,
        label=f"Holiday ({holiday})",
    )
    ax.axvline(pd.Timestamp(saturday), linestyle="--", linewidth=0.8, alpha=0.6)
    ax.axvline(
        pd.Timestamp(holiday) + pd.Timedelta(days=1),
        linestyle="--",
        linewidth=0.8,
        alpha=0.6,
    )

_ = plt.tight_layout(rect=[0, 0, 1, 0.96])
