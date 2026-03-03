# busdayaxis

[![PyPI](https://img.shields.io/pypi/v/busdayaxis)](https://pypi.org/project/busdayaxis/)
[![License](https://img.shields.io/badge/License-BSD--3--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)

## Business-day axis support for Matplotlib.

`busdayaxis` provides a custom Matplotlib scale that compresses non-business days and displays time in continuous business-day space.
- Useful when your data has no weekend activity and is naturally defined in business-day units.
- Integrates directly with Matplotlib’s transformation and autoscaling machinery.
- No data preprocessing is required.
- Custom business calendars are supported.

## Motivation
Many time series evolve in business time rather than calendar time:
- Equity prices
- Trading signals
- Portfolio returns
- Risk metrics
- Operational KPIs

When plotted on a standard calendar axis, weekends introduce artificial gaps that visually distort slopes and compress active trading periods.
`busdayaxis` removes these inactive periods by mapping calendar datetimes to continuous business-day units.

## Installation
You can install using `pip`:

```bash
pip install busdayaxis
```

## Quick Start

```python
import matplotlib.pyplot as plt
import busdayaxis

busdayaxis.register_scale()

ax.plot(dates, values)
ax.set_xscale("busday")
```


## Custom Business Calendars

The scale supports all keyword arguments accepted by NumPy’s business-day functions (is_busday, busday_count, busday_offset). This allows custom weekmasks and holiday lists.

```python
ax.set_xscale(
    "busday",
    weekmask="Mon Tue Wed Thu Fri",
    holidays=["2025-01-01", "2025-12-25"],
)
```

This makes it possible to model exchange holidays or company-specific calendars.

## Matplotlib Integration

- The busday scale is implemented as a proper ScaleBase subclass and:
- Participates in Matplotlib’s transform pipeline
- Works with autoscaling
- Works with shared axes and subplots
- Supports all artists that go through the standard data transformation system
- This includes plot, scatter, bar, vlines, fill_between, and other common Matplotlib objects.

## License

BSD 3-Clause
