"""# Centering Day Labels with MidBusdayLocator

``MidBusdayLocator`` places one tick at the midpoint of each business session.
This is useful for day labels on the minor axis: the label sits visually
centered inside the session rather than at midnight or session open.

Core code:

```python
ax.xaxis.set_minor_locator(busdayaxis.MidBusdayLocator())
ax.xaxis.set_minor_formatter(mdates.DateFormatter("%a"))
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
CLOSE = 17

num_days = 5
dates = pd.date_range("2025-01-06", periods=num_days * 24, freq="h")
returns = np.random.normal(0, 0.002, len(dates))
returns[(dates.hour < OPEN) | (dates.hour >= CLOSE)] = 0.0
returns[dates.weekday >= 5] = 0.0
prices = 100 * (1 + pd.Series(returns, index=dates)).cumprod()

fig, ax = plt.subplots(figsize=(10, 4))

ax.plot(dates, prices.values, linewidth=1.3)

ax.set_xscale("busday", bushours=(OPEN, CLOSE))

ax.xaxis.set_major_locator(busdayaxis.DayLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter(""))
ax.xaxis.set_minor_locator(busdayaxis.MidBusdayLocator())
ax.xaxis.set_minor_formatter(mdates.DateFormatter("%A"))
ax.xaxis.grid(True, which="major")

ax.set_title("Day labels centered in session using MidBusdayLocator")
ax.set_ylabel("Price")

plt.tight_layout()
plt.show()
