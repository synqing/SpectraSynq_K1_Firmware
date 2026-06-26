# Types Reference

## Contents
- Core types
- tzinfo types
- Type annotations
- Compatibility notes

## Core Types

### `datetime.datetime`

All dateutil functions return or accept stdlib `datetime.datetime`. dateutil never introduces its own datetime subclass—the return type is always `datetime`.

```python
from datetime import datetime
from dateutil.parser import parse

result: datetime = parse("2026-06-11T14:23:01+08:00")
assert type(result) is datetime
```

### `dateutil.relativedelta.relativedelta`

Represents a calendar-aware duration. Fields: `years`, `months`, `days`, `hours`, `minutes`, `seconds`, `microseconds`, `weekday`.

```python
from dateutil.relativedelta import relativedelta, MO

rd = relativedelta(months=1, days=-3, weekday=MO(+1))
```

Arithmetic with `weekday` anchor is NOT commutative—`dt + rd` differs from `rd + dt`. Always put `datetime` on the left.

### `dateutil.rrule.rrule`

Recurrence iterator. Returns `datetime` objects. In test fixtures use `list(rrule(...))` immediately; don't hold live iterators across fixture teardown.

```python
from dateutil.rrule import rrule, DAILY
from dateutil.tz import tzutc

dates = list(rrule(DAILY, count=5, dtstart=datetime(2026, 6, 1, tzinfo=tzutc())))
```

## tzinfo Types

| Type | When to Use |
|------|-------------|
| `tzutc()` | UTC — canonical for all test timestamp storage |
| `tzoffset(name, seconds)` | Fixed offset (`+08:00 = tzoffset(None, 28800)`) |
| `gettz("Region/City")` | IANA DST-aware zone |
| `tzlocal()` | **AVOID in tests** — machine-dependent, non-reproducible |

### WARNING: `tzlocal()` in Test Fixtures

```python
# BAD — test result depends on CI machine timezone
from dateutil.tz import tzlocal
ts = datetime.now(tz=tzlocal())

# GOOD — deterministic
from dateutil.tz import tzutc
ts = datetime.now(tz=tzutc())
```

## Type Annotations

```python
from datetime import datetime
from dateutil.relativedelta import relativedelta

def elapsed(start: datetime, end: datetime) -> relativedelta:
    return relativedelta(end, start)

def shift_months(dt: datetime, n: int) -> datetime:
    return dt + relativedelta(months=n)
```

## Compatibility Notes

- `dateutil.parser.parse` returns `datetime`, never `date` (even for date-only strings)
- `relativedelta` is **not** a `timedelta` subclass — don't pass it to APIs expecting `timedelta`
- `tzinfo` objects from `gettz` are picklable; `tzlocal` objects are not