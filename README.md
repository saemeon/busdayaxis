[![PyPI](https://img.shields.io/pypi/v/busdayaxis)](https://pypi.org/project/busdayaxis/)
[![License](https://img.shields.io/badge/License-BSD--3--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)

# busdayaxis

A Matplotlib scale that compresses non-business days and off-hours. Every visible unit on the axis corresponds to active time — no gaps for weekends, holidays, or overnight periods. No data preprocessing needed.

![Remove weekend gaps](https://raw.githubusercontent.com/saemeon/busdayaxis/master/docs/assets/remove_weekend.png)

**Full documentation at [saemeon.github.io/busdayaxis](https://saemeon.github.io/busdayaxis/)**

## Installation

```bash
pip install busdayaxis
```

## Quick Start

```python
import matplotlib.pyplot as plt
import pandas as pd
import busdayaxis

busdayaxis.register_scale()  # register once at the start of your script

dates = pd.date_range("2026-01-01", periods=10, freq="B")
values = range(len(dates))

fig, ax = plt.subplots()
ax.plot(dates, values)
ax.set_xscale("busday", bushours=(9, 17))  # compress weekends (Mon–Fri default) and off-hours (17:00–09:00 in this example)
plt.show()
```

## Why

Time series that only evolve on business days — prices, signals, operational metrics — look distorted on a standard calendar axis. Weekends and holidays introduce flat gaps that compress active periods and visually skew slopes. `busdayaxis` removes these gaps entirely.

## What it provides

- Compress weekends, holidays, and overnight gaps by adding an `axis scale`with  a single call:

    ```python
    ax.set_xscale("busday", weekmask=..., holidays=..., busdaycal=..., bushours=...)
    ```

    - `weekmask`, `holidays`, `busdaycal`: standard `numpy.is_busday` parameters to configure which days are considered business days

    - `bushours`: define uniform or weekday-specific business hours

    - Implemented as a proper `matplotlib.scale.ScaleBase` subclass — autoscaling, shared axes, and all standard artists work without any changes to your plotting code

- Business-day-aware `DateLocator` wrappers for all standard `matplotlib.dates` locators — automatically filter out ticks on off-days and off-hours

- `BusdayLocator` base class to wrap any custom or third-party date locator with the same business-day filtering logic

- `MidBusdayLocator` to place a tick at the midpoint of each business session, useful for centering day labels

## Under the Hood

- ``matplotlib`` internally handles dates as floating-point numbers representing **days since 1970-01-01**, or stated alternatively, as

    $$\text{ matplotlib-representation}=\frac{\text{hours\ since\ 1970-01-01}}{24\ \text{hours}}$$

- `busdayaxis` transforms these coordinates to floating-point numbers representing

    $$\text{busdayaxis-representation} = \frac{\text{business-hours since 1970-01-01}}{24 \text{ hours}}$$

    This conversion implies that datetime values that fall on non-business days or outside of business hours will be mapped to the same coordinate as the nearest preceding business hour. For example, if business hours are defined as 9:00 to 17:00, then "1970-01-05 08:00" (Mon 08:00) is mapped to the same coordinate as "1970-01-05 09:00" (Mon 09:00), because the earlier timestamp lies outside the defined business hours.


### Example: "1970-01-05 10:00" (Mon 10:00)

- Matplotlib representation (all hours counted):


          Thu 1970-01-01   24h (00:00 - 24:00)
        + Fri 1970-01-02   24h (00:00 - 24:00)
        + Sat 1970-01-03   24h (00:00 - 24:00)
        + Sun 1970-01-04   24h (00:00 - 24:00)
        + Mon 1970-01-05   10h (00:00 - 10:00)
        ---------------------------------------
        =                  106h (Total hours since epoch)
        /                  24h
        ---------------------------------------
        =                  4.41666... (matplotlib coordinate)

- Busdayaxis representation:
    - We assume here that  business hours are from 9:00 to 17:00. This can be configured by setting `ax.set_xscale("busday", bushours=(9, 17))`.

    To get the floating-point representation of "1970-01-05 10:00" (Mon 10:00), we count the business hours that have elapsed since 1970-01-01 00:00:

          Thu 1970-01-01   8h (9:00 - 17:00)
        + Fri 1970-01-02   8h (9:00 - 17:00)
        + Sat 1970-01-03   0h
        + Sun 1970-01-04   0h
        + Mon 1970-01-05   1h (09:00 - 10:00)
        ---------------------------------------
        =                 17h (business hours since epoch)
        /                  24h
        ---------------------------------------
        =          0.708333... (busdayaxis coordinate)

## License

BSD 3-Clause
