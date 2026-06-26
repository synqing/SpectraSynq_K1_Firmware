# Patterns Reference

## Contents
- Parsing patterns
- Timezone patterns
- Relative delta patterns
- Anti-patterns

## Parsing Patterns

### DO: Provide a `default` to anchor missing fields

```python
from dateutil.parser import parse
from datetime import datetime
from dateutil.tz import tzutc

# GOOD — missing date fields fall back to known anchor, not today
ts = parse("14:23:01", default=datetime(2026, 1, 1, tzinfo=tzutc()))
```

Without `default`, missing fields silently use `datetime.today()`. In replay tests run on different days, this produces non-deterministic results.

### DO: Use `parserinfo` for non-English month names in fixtures

```python
from dateutil.parser import parse, parserinfo

class MYParserInfo(parserinfo):
    MONTHS = [("Jan", "Januari"), ("Feb", "Februari"), ...]  # new code to add

ts = parse("11 Jun 2026", parserinfo=MYParserInfo())
```

### WARNING: Fuzzy Parsing in Production Paths

**The Problem:**
```python
# BAD — fuzzy=True silently ignores unrecognised tokens
ts = parse("onset_event: 2026-06-11T14:23:01 [mode=7]", fuzzy=True)
```

**Why This Breaks:**
1. Silently drops content that may be load-bearing (e.g., mode token parsed as part of date)
2. No guarantee which tokens are consumed — output varies with dateutil version
3. In replay harnesses, a wrong timestamp corrupts the entire event sequence

**The Fix:**
```python
# GOOD — pre-strip known noise, then parse cleanly
import re
raw = "onset_event: 2026-06-11T14:23:01 [mode=7]"
match = re.search(r'\d{4}-\d{2}-\d{2}T[\d:]+', raw)
ts = parse(match.group()) if match else None
```

## Timezone Patterns

### DO: Always produce timezone-aware datetimes in test fixtures

```python
from dateutil.tz import tzutc, gettz

# GOOD
ts_utc = parse("2026-06-11T06:23:01Z").replace(tzinfo=tzutc())
ts_local = parse("2026-06-11T14:23:01").replace(tzinfo=gettz("Asia/Kuala_Lumpur"))
```

### DO: Normalise to UTC before persisting or comparing

```python
from dateutil.tz import tzutc

def to_utc(dt: datetime) -> datetime:
    return dt.astimezone(tzutc())
```

### WARNING: Mixing naive and aware datetimes

```python
# BAD — raises TypeError at comparison, or silently wrong if using subtraction hacks
naive = datetime(2026, 6, 11, 14, 23, 1)
aware = datetime(2026, 6, 11, 6, 23, 1, tzinfo=tzutc())
delta = aware - naive  # TypeError
```

## Relative Delta Patterns

### Use `relativedelta` only for calendar arithmetic

```python
from dateutil.relativedelta import relativedelta

# GOOD — month boundary crossing
next_month = ts + relativedelta(months=1)

# UNNECESSARY — use timedelta for fixed durations
# BAD
delta = relativedelta(seconds=5)
# GOOD
delta = timedelta(seconds=5)
```

`relativedelta` is heavier than `timedelta`. Reach for it only when months/years are involved.