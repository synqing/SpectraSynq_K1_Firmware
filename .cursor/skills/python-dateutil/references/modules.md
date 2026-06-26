# Modules Reference

## Contents
- `dateutil.parser`
- `dateutil.tz`
- `dateutil.relativedelta`
- `dateutil.rrule`
- Module selection guide

## `dateutil.parser`

**Use:** Parsing ambiguous or non-ISO timestamp strings from serial transcripts and test fixtures.

```python
from dateutil.parser import parse, ParserError

# Strict parsing — raises ParserError on failure (preferred over silent None)
try:
    ts = parse(raw_string)
except ParserError as e:
    raise ValueError(f"Unparseable timestamp in fixture: {raw_string!r}") from e
```

**Do not** use `parse()` on untrusted input without a try/except—malformed strings raise `ParserError`, not return `None`.

## `dateutil.tz`

**Use:** Attaching correct timezone to parsed timestamps; converting between zones for UTC-normalised storage.

```python
from dateutil.tz import tzutc, tzoffset, gettz

UTC = tzutc()
KL = gettz("Asia/Kuala_Lumpur")  # UTC+8, DST-aware
FIXED_8 = tzoffset("MYT", 8 * 3600)  # fixed offset, no DST
```

`gettz` reads the system IANA database. In CI containers that lack `tzdata`, it may return `None`—guard:

```python
zone = gettz("Asia/Kuala_Lumpur")
assert zone is not None, "tzdata not installed — pip install tzdata"
```

## `dateutil.relativedelta`

**Use:** Calendar arithmetic (adding months, anchoring to weekdays) in test timeline generation.

```python
from dateutil.relativedelta import relativedelta, MO, FR

# Last Friday of current month
last_friday = datetime(2026, 6, 30, tzinfo=tzutc()) + relativedelta(weekday=FR(-1))

# One month forward, clamped to valid day
next = datetime(2026, 1, 31, tzinfo=tzutc()) + relativedelta(months=1)
# → 2026-02-28 (not 2026-03-03)
```

## `dateutil.rrule`

**Use:** Generating deterministic date sequences for parameterised test cases.

```python
from dateutil.rrule import rrule, WEEKLY, MO
from dateutil.tz import tzutc

# Every Monday for 4 weeks starting 2026-06-01
mondays = list(rrule(WEEKLY, byweekday=MO, count=4,
                     dtstart=datetime(2026, 6, 1, tzinfo=tzutc())))
```

**Materialise immediately** with `list()`. Lazy rrule iterators hold state; sharing across parametrize calls produces wrong sequences.

## Module Selection Guide

| Task | Reach for |
|------|-----------|
| Parse ISO 8601 string | `datetime.fromisoformat()` (stdlib, no dep) |
| Parse ambiguous/unknown format | `dateutil.parser.parse` |
| Add N months to a date | `dateutil.relativedelta` |
| Add N days/hours/seconds | `datetime.timedelta` (stdlib) |
| Named timezone | `dateutil.tz.gettz` |
| UTC only | `datetime.timezone.utc` (stdlib) or `dateutil.tz.tzutc()` |
| Recurrence sequences | `dateutil.rrule` |

See the **pytest** skill for fixture parametrize integration with rrule sequences.