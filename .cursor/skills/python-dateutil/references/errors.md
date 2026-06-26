# Errors Reference

## Contents
- `ParserError`
- Timezone errors
- Arithmetic errors
- Fixture-specific error patterns

## `ParserError`

Raised by `dateutil.parser.parse` when the input cannot be interpreted as a date.

```python
from dateutil.parser import parse, ParserError

# GOOD — explicit catch, re-raise with context
try:
    ts = parse(raw)
except ParserError as e:
    raise ValueError(f"Bad timestamp in harness fixture: {raw!r}") from e
```

**Do not** catch bare `Exception` to swallow this—a bad timestamp in a replay fixture means the fixture itself is corrupt.

### WARNING: `OverflowError` on extreme values

```python
# BAD — year 9999+ triggers OverflowError, not ParserError
parse("99999-01-01")  # OverflowError

# GOOD — catch both in transcript ingest
try:
    ts = parse(raw)
except (ParserError, OverflowError, ValueError) as e:
    log.warning("Skipping unparseable timestamp %r: %s", raw, e)
    ts = None
```

## Timezone Errors

### `gettz` returning `None`

`gettz("Invalid/Zone")` returns `None` silently instead of raising.

```python
from dateutil.tz import gettz

zone = gettz("Asia/Kuala_Lumpur")
if zone is None:
    raise RuntimeError("tzdata package not installed or zone name invalid")
```

This is the most common silent bug in CI environments that use slim container images without `tzdata`.

### Naive/aware `TypeError` in comparisons

```python
# Symptom: TypeError: can't compare offset-naive and offset-aware datetimes
# Cause: one side of - or < is naive

# Fix: enforce UTC-aware at parse time
def safe_parse(s: str) -> datetime:
    dt = parse(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tzutc())
    return dt
```

## Arithmetic Errors

### `relativedelta` order matters for `weekday`

```python
from dateutil.relativedelta import relativedelta, MO

base = datetime(2026, 6, 11, tzinfo=tzutc())  # Wednesday

# WRONG order — weekday applied before month shift
wrong = relativedelta(months=1, weekday=MO(+1)) + base

# RIGHT order — shift month first, then snap to weekday
right = base + relativedelta(months=1) + relativedelta(weekday=MO(+1))
```

Always chain two `relativedelta` additions rather than combining `months` + `weekday` in one object when the snap must occur after the shift.

## Fixture-Specific Error Patterns

### Non-deterministic parse from `default=datetime.today()`

```python
# BAD — today changes every day; breaks replay regression
ts = parse("14:23:01")  # default=datetime.today() used internally

# GOOD — anchor to epoch of the test fixture
FIXTURE_EPOCH = datetime(2026, 6, 1, tzinfo=tzutc())
ts = parse("14:23:01", default=FIXTURE_EPOCH)
```

See the **pytest** skill for fixture epoch constants and parametrize patterns.