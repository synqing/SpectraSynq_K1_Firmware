# aiofiles Patterns Reference

## Contents
- Core Read/Write Patterns
- Binary I/O
- JSON and Structured Data
- Anti-Patterns
- Error Handling

---

## Core Read/Write Patterns

### Full read
```python
async with aiofiles.open(path, encoding="utf-8") as f:
    content = await f.read()
```

### Chunked read (large files)
```python
# new code to add
CHUNK = 65536  # 64 KB

async def stream_chunks(path: str):
    async with aiofiles.open(path, "rb") as f:
        while chunk := await f.read(CHUNK):
            yield chunk
```

### Atomic write (write-then-rename)
```python
# new code to add
import os

async def atomic_write(path: str, data: str) -> None:
    tmp = path + ".tmp"
    async with aiofiles.open(tmp, "w", encoding="utf-8") as f:
        await f.write(data)
        await f.flush()
    os.replace(tmp, path)  # atomic on POSIX; os.replace is sync but instant
```

**Why atomic write matters:** Direct `open(path, "w")` truncates the file immediately. A crash mid-write leaves a corrupt file. Write-then-rename is the standard mitigation.

---

## Binary I/O

```python
async def copy_binary(src: str, dst: str) -> None:
    async with aiofiles.open(src, "rb") as r, aiofiles.open(dst, "wb") as w:
        while chunk := await r.read(65536):
            await w.write(chunk)
```

---

## JSON and Structured Data

aiofiles has no built-in JSON support. Combine with `json` stdlib:

```python
import json

async def read_json(path: str) -> dict:
    async with aiofiles.open(path, encoding="utf-8") as f:
        return json.loads(await f.read())

async def write_json(path: str, data: dict) -> None:
    payload = json.dumps(data, indent=2, ensure_ascii=False)
    async with aiofiles.open(path, "w", encoding="utf-8") as f:
        await f.write(payload)
```

---

## Anti-Patterns

### WARNING: Sync `open()` inside async functions

**The Problem:**
```python
# BAD - blocks the event loop
async def handler():
    with open("data.txt") as f:
        return f.read()
```

**Why This Breaks:**
1. `open()` and `read()` are blocking syscalls — they stall the entire event loop thread.
2. Under concurrent requests, all coroutines freeze while one reads a slow file (NFS, large file, slow disk).
3. Intermittent latency spikes appear under load that vanish in local testing.

**The Fix:**
```python
async def handler():
    async with aiofiles.open("data.txt", encoding="utf-8") as f:
        return await f.read()
```

---

### WARNING: Using aiofiles for tiny, hot-path files

**The Problem:**
```python
# QUESTIONABLE - thread pool overhead for a 200-byte config read
async def get_version():
    async with aiofiles.open("VERSION", encoding="utf-8") as f:
        return (await f.read()).strip()
```

**Why This Is Often Wrong:**
1. aiofiles dispatches to a thread pool executor — there is real overhead per call (~0.1–0.5 ms).
2. For files read once at startup (configs, version strings), sync `open()` at module init is simpler and faster.
3. The thread pool adds latency, not removes it, when disk cache is hot and no other coroutines are competing.

**The Fix:** Read once at startup synchronously; cache the result.

```python
# new code to add
with open("VERSION", encoding="utf-8") as f:
    APP_VERSION = f.read().strip()
```

---

### WARNING: Forgetting `await` on file methods

**The Problem:**
```python
# BAD - returns a coroutine object, not the data
async with aiofiles.open(path) as f:
    content = f.read()  # missing await
```

**Why This Breaks:** `f.read()` returns a coroutine. `content` will be `<coroutine object ...>`, causing silent downstream failures (wrong type passed to string operations, unexpected `None` after `str()` coercion).

**The Fix:** Every file method call requires `await`.

---

## Error Handling

```python
# new code to add
import aiofiles
from pathlib import Path

async def safe_read(path: str, default: str = "") -> str:
    try:
        async with aiofiles.open(path, encoding="utf-8") as f:
            return await f.read()
    except FileNotFoundError:
        return default
    except PermissionError as e:
        raise RuntimeError(f"Cannot read {path}: {e}") from e
```

Catch `FileNotFoundError` and `PermissionError` explicitly. Bare `except Exception` silences encoding errors and OS-level failures that indicate real problems.