# httpx Workflows Reference

## Contents
- Testing with respx
- Parallel Requests
- Pagination
- Diagnostic / Logging
- Integration Checklist

---

## Testing with respx

Mock httpx at the transport layer using `respx`. Never patch `httpx.get` — it bypasses the client under test.

```python
# new code to add
import respx
import httpx
import pytest

@pytest.mark.asyncio
@respx.mock
async def test_fetch_data():
    respx.get("https://api.example.com/data").mock(
        return_value=httpx.Response(200, json={"value": 42})
    )

    async with httpx.AsyncClient(base_url="https://api.example.com") as client:
        r = await client.get("/data")
        assert r.json() == {"value": 42}
```

For error path tests:

```python
# new code to add
@respx.mock
async def test_handles_500():
    respx.get("https://api.example.com/data").mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )
    with pytest.raises(httpx.HTTPStatusError):
        async with httpx.AsyncClient() as client:
            (await client.get("https://api.example.com/data")).raise_for_status()
```

See the **pytest** skill for `pytest-asyncio` configuration.

---

## Parallel Requests

Use `asyncio.gather()` to fan out requests concurrently. All requests share the same client connection pool — set `max_connections` to match your target parallelism.

```python
# new code to add
import asyncio
import httpx

async def fetch_all(urls: list[str]) -> list[dict]:
    async with httpx.AsyncClient(
        timeout=10.0,
        limits=httpx.Limits(max_connections=len(urls)),
    ) as client:
        responses = await asyncio.gather(
            *[client.get(url) for url in urls],
            return_exceptions=True,
        )

    results = []
    for url, r in zip(urls, responses):
        if isinstance(r, Exception):
            results.append({"url": url, "error": str(r)})
        else:
            r.raise_for_status()
            results.append(r.json())
    return results
```

`return_exceptions=True` prevents a single failure from cancelling all other in-flight requests.

---

## Pagination

Cursor-based pagination pattern:

```python
# new code to add
async def fetch_all_pages(client: httpx.AsyncClient, url: str) -> list[dict]:
    items = []
    params: dict = {}

    while True:
        r = await client.get(url, params=params)
        r.raise_for_status()
        body = r.json()
        items.extend(body["data"])

        cursor = body.get("next_cursor")
        if not cursor:
            break
        params = {"cursor": cursor}

    return items
```

**WARNING:** Add a hard page cap in production — a misbehaving API returning infinite pages will OOM the process.

```python
MAX_PAGES = 100
for page_num in range(MAX_PAGES):
    ...
    if not cursor:
        break
else:
    raise RuntimeError(f"Pagination exceeded {MAX_PAGES} pages")
```

---

## Diagnostic / Logging

Hook into httpx event hooks for structured logging without wrapping every call:

```python
# new code to add
import logging
import httpx

logger = logging.getLogger("http")

def log_request(request: httpx.Request) -> None:
    logger.debug("→ %s %s", request.method, request.url)

def log_response(response: httpx.Response) -> None:
    logger.debug("← %d %s (%.2fs)", response.status_code, response.url,
                 response.elapsed.total_seconds())

client = httpx.AsyncClient(
    event_hooks={
        "request": [log_request],
        "response": [log_response],
    }
)
```

`response.elapsed` is only available after the response body is fully read — unavailable inside `stream()`.

---

## Integration Checklist

Copy this checklist when wiring httpx into a new service:

```
- [ ] AsyncClient instantiated once at app startup (not per-request)
- [ ] Explicit Timeout set on client (connect + read + write + pool)
- [ ] Limits.max_connections sized for expected concurrency
- [ ] raise_for_status() called on every non-streaming response
- [ ] HTTPStatusError, TimeoutException, NetworkError caught separately
- [ ] Client closed on app shutdown (aclose() or lifespan handler)
- [ ] respx mocks in place for all HTTP calls in unit tests
- [ ] Auth credentials sourced from env vars, not hardcoded
```