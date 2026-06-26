# httpx Patterns Reference

## Contents
- Client Lifecycle
- Timeouts
- Error Handling
- Auth Patterns
- Streaming
- Anti-Patterns

---

## Client Lifecycle

**ALWAYS** use a shared `AsyncClient` per application lifetime, not a new client per request. Creating a client per-call bypasses connection pooling — under load this opens a new TCP connection for every request, exhausting OS file descriptors.

```python
# new code to add
# app startup
client = httpx.AsyncClient(
    base_url="https://api.example.com",
    timeout=httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0),
    limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    headers={"User-Agent": "SensoryBridge/1.0"},
)

# app shutdown
await client.aclose()
```

---

## Timeouts

**NEVER** use `httpx.AsyncClient()` without a timeout. The default is no timeout — a hung server will block your coroutine indefinitely.

```python
# BAD — no timeout
async with httpx.AsyncClient() as client:
    r = await client.get(url)  # hangs forever if server stalls

# GOOD — explicit per-phase timeouts
timeout = httpx.Timeout(connect=3.0, read=10.0, write=5.0, pool=1.0)
async with httpx.AsyncClient(timeout=timeout) as client:
    r = await client.get(url)
```

Use `httpx.Timeout` with named phases, not a single float, so connection stalls and slow reads fail independently.

---

## Error Handling

`raise_for_status()` raises `httpx.HTTPStatusError` on 4xx/5xx. Catch it specifically — bare `except Exception` masks bugs.

```python
# new code to add
async def call_api(client: httpx.AsyncClient, path: str) -> dict:
    try:
        r = await client.get(path)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as e:
        # e.response.status_code, e.response.text available
        raise RuntimeError(f"API error {e.response.status_code}: {e.response.text}") from e
    except httpx.TimeoutException:
        raise RuntimeError(f"Request to {path} timed out") from None
    except httpx.NetworkError as e:
        raise RuntimeError(f"Network failure: {e}") from e
```

Error hierarchy worth knowing:
- `httpx.TimeoutException` — connect, read, write, pool timeout
- `httpx.NetworkError` — DNS, connection refused, SSL
- `httpx.HTTPStatusError` — 4xx/5xx (only raised by `raise_for_status()`)

---

## Auth Patterns

Pass auth to the client (applied to all requests) or override per-request.

```python
# Bearer token via custom auth class
class BearerAuth(httpx.Auth):
    def __init__(self, token: str):
        self.token = token

    def auth_flow(self, request):
        request.headers["Authorization"] = f"Bearer {self.token}"
        yield request

client = httpx.AsyncClient(auth=BearerAuth(token))
```

For token refresh (OAuth), implement a two-step `auth_flow` that retries on 401:

```python
# new code to add
def auth_flow(self, request):
    request.headers["Authorization"] = f"Bearer {self._token}"
    response = yield request
    if response.status_code == 401:
        self._token = self._refresh()
        request.headers["Authorization"] = f"Bearer {self._token}"
        yield request
```

---

## Streaming

Use `client.stream()` for responses that may be large — it avoids loading the full body into memory.

```python
# new code to add
async def download_to_file(client: httpx.AsyncClient, url: str, path: str) -> None:
    async with client.stream("GET", url) as response:
        response.raise_for_status()
        with open(path, "wb") as f:
            async for chunk in response.aiter_bytes(chunk_size=8192):
                f.write(chunk)
```

**WARNING:** `response.content` and `response.json()` are unavailable inside `stream()` — they require the full body. Use `aiter_bytes()` or `aiter_text()`.

---

## Anti-Patterns

### WARNING: New client per request

**The Problem:**
```python
# BAD — creates a new TCP connection every call
async def get(url):
    async with httpx.AsyncClient() as client:
        return await client.get(url)
```

**Why This Breaks:**
1. No connection reuse — new TCP handshake per request (adds ~100ms+ latency)
2. Under concurrency, exhausts OS socket limits
3. Ignores HTTP/2 multiplexing entirely

**The Fix:** Share a single `AsyncClient` across the application lifetime.

---

### WARNING: Sync client inside async function

**The Problem:**
```python
# BAD — blocks the event loop
async def fetch():
    return httpx.get(url).json()  # sync call in async context
```

**Why This Breaks:** Blocks the entire event loop thread for the duration of the request. All other coroutines stall.

**The Fix:** Use `httpx.AsyncClient` and `await`.