# busdayaxis

[![PyPI](https://img.shields.io/pypi/v/busdayaxis)](https://pypi.org/project/busdayaxis/)
[![License](https://img.shields.io/badge/License-BSD--3--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)

A Matplotlib scale that compresses non-business days and off-hours. Every visible unit on the axis corresponds to active time — no gaps for weekends, holidays, or overnight periods. No data preprocessing needed.

![Remove weekend gaps](https://raw.githubusercontent.com/saemeon/busdayaxis/master/docs/assets/remove_weekend.png)

**Full documentation at [saemeon.github.io/busdayaxis](https://saemeon.github.io/busdayaxis/)**

## Why

Time series that only evolve on business days — prices, signals, operational metrics — look distorted on a standard calendar axis: weekends and holidays introduce flat gaps that compress active periods and visually skew slopes. `busdayaxis` removes those gaps entirely.

## What it provides

- Compress weekends, holidays, and overnight gaps with a single `set_xscale("busday")` call
- Implemented as a proper `ScaleBase` subclass — autoscaling, shared axes, and all standard artists work without any changes to your plotting code
- Per-day session hours (`bushours`) — uniform, per-weekday list, or dict with sensible defaults
- Custom weekmasks and holiday lists, compatible with NumPy's busday calendar
- Business-day-aware wrappers for all standard Matplotlib date locators — each filters ticks to business days and hours automatically
- `MidBusdayLocator` to place a tick at the midpoint of each business session, useful for centering day labels
- `BusdayLocator` base class to wrap any custom or third-party locator

## Installation

```bash
pip install busdayaxis
```

## Quick Start

```python
import matplotlib.pyplot as plt
import busdayaxis

busdayaxis.register_scale()  # register once at the start of your script

fig, ax = plt.subplots()
ax.plot(dates, values)
ax.set_xscale("busday")  # compress weekends (Mon–Fri default)
```

## License

BSD 3-Clause
