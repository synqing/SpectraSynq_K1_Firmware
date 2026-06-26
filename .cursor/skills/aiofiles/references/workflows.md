# aiofiles Workflows Reference

## Contents
- Installation and Setup
- Async Test Patterns (pytest-asyncio)
- Concurrent File Processing
- Log Tailing
- Checklist: New Async File Operation

---

## Installation and Setup

```bash
pip install aiofiles
# With type stubs (recommended for typed projects):
pip install aiofiles types-aiofiles
```

Verify:
```bash
python -c "import aiofiles; print(aiofiles.__version__)"
```

---

## Async Test Patterns

See the **pytest** skill for full pytest-asyncio setup. For file I/O tests:

```python
# new code to add
import pytest
import aiofiles
from pathlib import Path

@pytest.mark.asyncio
async def test_write_and_read(tmp_path: Path):
    target = tmp_path / "output.txt"
    async with aiofiles.open(target, "w") as f:
        await f.write("hello")
    async with aiofiles.open(target) as f:
        assert await f.read() == "hello"
```

**Why `tmp_path`:** pytest's `tmp_path` fixture creates isolated directories per test. Never write to hardcoded paths in tests — parallel test runs collide.

---

## Concurrent File Processing

Process multiple files in parallel without spawning threads manually:

```python
# new code to add
import asyncio
import aiofiles
from pathlib import Path

async def process_file(path: Path) -> dict:
    async with aiofiles.open(path, encoding="utf-8") as f:
        content = await f.read()
    return {"path": str(path), "size": len(content), "lines": content.count("\n")}

async def process_directory(directory: Path, pattern: str = "*.txt") -> list[dict]:
    paths = list(directory.glob(pattern))
    return await asyncio.gather(*[process_file(p) for p in paths])
```

**Concurrency limit:** `asyncio.gather` with hundreds of files exhausts the thread pool. Use a semaphore for large batches:

```python
# new code to add
async def process_directory_bounded(directory: Path, max_concurrent: int = 20) -> list[dict]:
    sem = asyncio.Semaphore(max_concurrent)
    paths = list(directory.glob("*.txt"))

    async def bounded(p: Path) -> dict:
        async with sem:
            return await process_file(p)

    return await asyncio.gather(*[bounded(p) for p in paths])
```

---

## Log Tailing (streaming append)

```python
# new code to add
import asyncio
import aiofiles

async def tail_log(path: str, poll_interval: float = 0.5):
    async with aiofiles.open(path, encoding="utf-8") as f:
        await f.seek(0, 2)  # seek to end
        while True:
            line = await f.readline()
            if line:
                yield line.rstrip()
            else:
                await asyncio.sleep(poll_interval)
```

**Note:** `f.seek()` and `f.tell()` are available on aiofiles handles but are synchronous wrappers — they do not block the loop because file position tracking is in-process state, not a syscall.

---

## Checklist: New Async File Operation

Copy this checklist and track progress:

- [ ] Import `aiofiles` (not `open`)
- [ ] Use `async with aiofiles.open(...)` — never bare `open()` in async context
- [ ] `await` every file method: `read()`, `write()`, `readline()`, `readlines()`, `flush()`
- [ ] Specify `encoding="utf-8"` for text mode (avoids platform-specific default encoding bugs)
- [ ] For writes: consider atomic write-then-rename if data loss on crash is unacceptable
- [ ] For large files: stream with `async for line in f:` or chunked `read(N)` — don't `read()` unboundedly
- [ ] For batch ops: add `asyncio.Semaphore` if processing >20 files concurrently
- [ ] Add `FileNotFoundError` / `PermissionError` handling at the call site
- [ ] Write tests with `tmp_path` fixture and `@pytest.mark.asyncio`

---

## DO / DON'T Summary

| DO | DON'T |
|----|-------|
| `async with aiofiles.open(p) as f:` | `with open(p) as f:` inside async |
| `await f.read()` | `f.read()` (returns coroutine) |
| Read once at startup for immutable configs | Re-open a hot config file per request with aiofiles |
| Use semaphore for >20 concurrent opens | `gather(*[open(p) for p in thousands_of_files])` |
| Atomic write for critical state files | Truncate-then-write for files that must survive crashes |