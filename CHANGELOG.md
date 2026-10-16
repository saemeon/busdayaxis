# Changelog

## [Unreleased]

- Fix `PendingDeprecationWarning` from Matplotlib 3.11: `BusdayScale` no longer
  takes an `axis` parameter. Passing one (`BusdayScale(ax.xaxis, ...)`) is still
  accepted and ignored, so older Matplotlib versions keep working.
- Update class-based examples in the docs to `BusdayScale(...)` without `ax.xaxis`.
- Add Python 3.14 to the CI test matrix.
- Add docs deployment workflow (MkDocs + `mike`).
- Add Dependabot configuration.
- Add locator gallery example (`plot_9_locators.py`).
- Complete the API reference.
- Increase test coverage.

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
