# Changelog

## [0.3.1] — 2026-10-20

### Fixed

- Passing `keep_midnight_ticks` positionally works again, as in 0.2.1, e.g.
  `BusdayLocator(mdates.DayLocator(), True)` or `HourLocator(True)`. It now
  emits a `DeprecationWarning`; use `keep_midnight_ticks=True` instead.
  Non-bool positional arguments are still forwarded to Matplotlib, so
  `HourLocator([9, 12])` keeps working.

## [0.3.0] — 2026-10-16

### Fixed

- Matplotlib 3.11 compatibility: importing `busdayaxis` no longer emits a
  `PendingDeprecationWarning` about the scale's `axis` parameter. Matplotlib
  plans to remove that parameter in 3.15, so this release keeps the package
  working with upcoming Matplotlib versions.
- NumPy 2.5 compatibility: no more `DeprecationWarning` about the "generic"
  datetime unit.
- Plots are no longer shifted or clipped when `rcParams["timezone"]` is set to
  something other than UTC. Datetimes are always treated as naive wall-clock
  time by the scale, the locators, `MidBusdayLocator` and `mark_gaps`, and the
  default tick labels match the plotted values.
- Calling `ax.set_xscale("busday")` *before* plotting dates no longer brings
  back tick marks on weekends and holidays.
- `NaN`/`NaT` x values no longer crash the plot; they leave a gap in the line,
  as on any other Matplotlib scale. Dates outside 1678–2262 are treated the
  same way instead of being placed at wrong positions.
- `holidays=` now accepts a `pandas.DatetimeIndex`, a `pandas.Series`, lists of
  `pandas.Timestamp` and `datetime64` arrays of any unit.
- Sub-second timestamps are no longer rounded to whole seconds, so
  millisecond data and `MicrosecondLocator` work. Converting axis positions
  back to dates (e.g. the cursor readout) is now exact instead of up to one
  second early.
- `HourLocator([9, 12])`, `WeekdayLocator(MO)` and the other locator wrappers
  now accept the same positional arguments as their `matplotlib.dates`
  counterparts. Previously the first argument was silently taken as
  `keep_midnight_ticks`.

### Performance

- Plotting large series is much faster: transforming 1 million points now
  takes about 15 ms instead of about 4 s.

### Changed

- `keep_midnight_ticks` is now keyword-only on all locators, e.g.
  `BusdayLocator(mdates.DayLocator(), keep_midnight_ticks=True)`.
- Locators with an `interval` (e.g. `HourLocator(interval=4)`) may place their
  ticks at different hours than before (e.g. 11:00/15:00 instead of
  10:00/14:00). Matplotlib counts such intervals from the left edge of the
  axis, which was previously computed one second too early. Pass explicit
  values such as `HourLocator(byhour=[10, 14])` for fixed tick positions.
- `BusdayScale` no longer needs the axis as its first argument. Write
  `ax.set_xscale(BusdayScale(bushours=(9, 17)))` instead of
  `BusdayScale(ax.xaxis, bushours=(9, 17))`. The old form still works, so no
  code changes are required.

### Documentation

- New gallery example comparing all business-day-aware tick locators.
- `AutoDateLocator` is now listed in the API reference.
- Class-based examples updated to the new `BusdayScale(...)` form.
- Python 3.14 is now tested.

## [0.2.1] — 2026-03-20

- Switch to MIT license.
- Raise minimum Python to 3.10.
- Add `_version.py` via `setuptools-scm`.
- Add `holidays_from_exchange()` utility.
- Add `mark_gaps()` utility (vline, broken, both).
- Add multi-interval `bushours` (e.g. lunch breaks).

## [0.1.3] — 2026-03-15

- Accept `str` and `datetime.time` for `bushours`.
- Add PEP 561 `py.typed` marker.
- Add type-checking CI job (`ty`).
- Migrate to `uv` for dependency management.
- Improve docs and docstrings.

## [0.1.2] — 2026-03-14

- Fix figure asset paths in docs.
- Add "Under the Hood" transform visualisation.

## [0.1.1] — 2026-03-10

- Fix division by zero when all weekday weights are zero.

## [0.1.0] — 2026-03-10

- `BusdayScale` registered as `"busday"`.
- `bushours`, `weekmask`, `holidays`, `busdaycal` parameters.
- Per-day `bushours` dict for weekday-specific schedules.
- Locator wrappers: `AutoDateLocator`, `DayLocator`, `HourLocator`,
  `MinuteLocator`, `SecondLocator`, `MicrosecondLocator`, `WeekdayLocator`.
- `MidBusdayLocator` for centred day labels.
- MkDocs Material docs with gallery examples.

## [0.0.2] — 2026-03-05

- Initial test suite.

## [0.0.1] — 2026-03-03

- Initial release.
