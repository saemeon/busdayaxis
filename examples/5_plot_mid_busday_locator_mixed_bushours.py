"""# MidBusdayLocator with Mixed Bushours

This example shows how to use the MidBusdayLocator to mark the middle of each business day
when using mixed bushours (different hours for different weekdays).

Core code:

```python
ax.set_xscale("busday", bushours={
    "Mon": (9, 17),
    "Tue": (9, 17),
    "Wed": (9, 12),
    "Thu": (9, 22),
    "Fri": (9, 12),
})
ax.xaxis.set_minor_locator(busdayaxis.MidBusdayLocator())
```
"""

# %%
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import busdayaxis

busdayaxis.register_scale()

OPEN = 9
bushours = {
    "Mon": (OPEN, 17),
    "Tue": (OPEN, 17),
    "Wed": (OPEN, 12),
    "Thu": (OPEN, 22),
    "Fri": (OPEN, 12),
}

# Derive close hour per weekday (Mon=0..Sun=6) directly from bushours
_day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
close_per_wd = np.array([bushours.get(name, (0, 0))[1] for name in _day_names])

num_days = 5
dates = pd.date_range("2025-01-06", periods=num_days * 24, freq="h")  # Mon–Fri

returns = np.random.normal(0, 0.002, len(dates))
close_hours = close_per_wd[dates.weekday]
returns[(dates.hour < OPEN) | (dates.hour >= close_hours)] = 0.0

prices = 100 * (1 + pd.Series(returns, index=dates)).cumprod()


fig, ax = plt.subplots()
ax.plot(dates, prices.values, linewidth=1.3)
ax.set_xscale("busday", bushours=bushours)
ax.xaxis.set_major_locator(busdayaxis.DayLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter(""))
ax.xaxis.set_minor_locator(busdayaxis.MidBusdayLocator())
ax.xaxis.set_minor_formatter(mdates.DateFormatter("%a"))
ax.xaxis.grid(True, which="major")
ax.xaxis.grid(False, which="minor")
ax.set_title("Business Time (scale='busday', bushours={per-day})")
ax.set_ylabel("Price")
plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.show()
