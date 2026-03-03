# mplbusdayaxis

A matplotlib scale for business days that skips weekends and holidays.

## Installation

```bash
pip install mplbusdayaxis
```

## Quick Start

```python
import matplotlib.pyplot as plt
import pandas as pd
import mplbusdayaxis as bda
import numpy as np

dates = pd.date_range("2024-01-01", periods=252, freq="D")
prices = 100 + np.cumsum(np.random.randn(252) * 2)

fig, ax = plt.subplots()
ax.plot(dates, prices)
ax.set_xscale("busday")
plt.show()
```

## Features

- **Business Day Scale**: X-axis scales based on business days only, skipping weekends
- **Holiday Support**: Specify custom holidays to exclude from the scale
- **Compatible with Matplotlib**: Works seamlessly with matplotlib's date handling
