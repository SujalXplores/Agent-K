# SigNoz MCP Server Setup — Agent K Investigation Loop

This runbook covers everything needed to get Agent K's investigation loop
working with a real SigNoz MCP server: building the binary, fixing the auth
header, generating an API key, and verifying a full investigation runs
end-to-end with evidence-backed claims.

## Prerequisites

- SigNoz running via Foundry inside WSL (see `RUNNING-AGENT-K.md` §4)
- Agent K app running on Windows (`uvicorn app.main:app --port 8000`)
- WSL Ubuntu with `wget` and `tar` available
- SigNoz UI accessible at http://localhost:8080 and logged in

## Step 1 — Build the SigNoz MCP server binary (Windows)

The MCP server ships no Windows binary in its GitHub releases. Build it
from source in WSL, cross-compiling for Windows.

### 1a. Install Go 1.25 in WSL (user-local, no sudo)

```powershell
wsl -d Ubuntu -- bash -c 'cd /tmp && wget -q https://go.dev/dl/go1.25.0.linux-amd64.tar.gz && mkdir -p ~/go-sdk && tar -C ~/go-sdk -xzf go1.25.0.linux-amd64.tar.gz && ~/go-sdk/go/bin/go version'
```

Expected output: `go version go1.25.0 linux/amd64`

### 1b. Clone the MCP server source

```powershell
wsl -d Ubuntu -- bash -c 'cd /tmp && git clone --depth 1 --branch v0.9.0 https://github.com/SigNoz/signoz-mcp-server.git signoz-mcp 2>&1 | tail -3'
```

### 1c. Patch the auth header (REQUIRED)

SigNoz v0.134 rejects JWTs sent via the `SIGNOZ-API-KEY` header. The MCP
server's stdio mode uses that header by default. Patch it to use
`Authorization: Bearer <jwt>` instead.

```powershell
wsl -d Ubuntu -- bash -c 'cd /tmp/signoz-mcp && sed -i "1001s|.*|                ctx = util.SetAPIKey(ctx, \"Bearer \"+m.config.APIKey)|" internal/mcp-server/server.go && sed -i "1002s|.*|                ctx = util.SetAuthHeader(ctx, \"Authorization\")|" internal/mcp-server/server.go'
```

Verify the patch:

```powershell
wsl -d Ubuntu -- bash -c 'sed -n "999,1005p" /tmp/signoz-mcp/internal/mcp-server/server.go'
```

Expected:
```go
        stdio := server.NewStdioServer(s)
        stdio.SetContextFunc(func(ctx context.Context) context.Context {
                ctx = util.SetAPIKey(ctx, "Bearer "+m.config.APIKey)
                ctx = util.SetAuthHeader(ctx, "Authorization")
                ctx = util.SetSigNozURL(ctx, m.config.URL)
```

### 1d. Cross-compile for Windows

```powershell
wsl -d Ubuntu -- bash -c 'export PATH=~/go-sdk/go/bin:$PATH; export GOPATH=~/go; cd /tmp/signoz-mcp && GOOS=windows GOARCH=amd64 CGO_ENABLED=0 go build -o /tmp/signoz-mcp-server.exe ./cmd/server/ 2>&1 | tail -5; ls -la /tmp/signoz-mcp-server.exe'
```

Expected: a ~50MB binary at `/tmp/signoz-mcp-server.exe`.

### 1e. Copy the binary to the project directory

```powershell
Copy-Item "\\wsl.localhost\Ubuntu\tmp\signoz-mcp-server.exe" "f:\Hackathon ideas\Agent-K\signoz-mcp-server.exe" -Force
```

## Step 2 — Generate a SigNoz API key (JWT)

SigNoz v0.134 EE requires a license for service-account API keys (the "Add
Key" button in Settings → Service Accounts is disabled without one). The
workaround is to use the browser session JWT as the API key.

### 2a. Log in to SigNoz

Open http://localhost:8080 in a browser and log in with your credentials.

### 2b. Extract the JWT from the browser

Open the browser's Developer Tools (F12) → Console, and run:

```javascript
localStorage.getItem('AUTH_TOKEN')
```

Copy the full JWT string (starts with `eyJ...`).

### 2c. Update `.env`

Set `SIGNOZ_API_KEY` in `f:\Hackathon ideas\Agent-K\.env`:

```
SIGNOZ_MCP_COMMAND=signoz-mcp-server.exe
SIGNOZ_URL=http://localhost:8080
SIGNOZ_API_KEY="<paste the JWT here>"
```

> **The JWT must be wrapped in double quotes** — it contains characters that
> confuse the dotenv parser otherwise.

> **The JWT expires every 30 minutes.** Before each demo run, reload the
> SigNoz UI page in the browser to refresh the token, then re-extract and
> update `.env`. See §5 below for the refresh procedure.

## Step 3 — Verify the MCP server works

### 3a. List available tools

The MCP tool inventory is pinned by `tests/test_signoz_mcp.py` and `tests/test_investigation.py` (which asserts the tool-name list against `signoz-mcp-server` v0.9.0's advertised inventory). Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_signoz_mcp.py -v
```

You should see the pinned tool list, including:
- `signoz_search_traces`
- `signoz_search_logs`
- `signoz_aggregate_traces`
- `signoz_get_trace_details`
- `signoz_list_services`

### 3b. Run a single trace query

To verify a real query end-to-end against a live stack, set the env vars and run the integration tests:

```powershell
$env:SIGNOZ_API_KEY = (.\.venv\Scripts\python.exe -c "from dotenv import dotenv_values; print(dotenv_values('.env')['SIGNOZ_API_KEY'])")
$env:SIGNOZ_URL = "http://localhost:8080"
$env:SIGNOZ_MCP_COMMAND = "signoz-mcp-server.exe"
.\.venv\Scripts\python.exe -m pytest tests/test_signoz_mcp.py -v
```

Expected: `isError: False` with real trace data in the `content` field.

If you see `isError: True` with `401: unauthenticated`, the JWT has expired
— go back to Step 2 and refresh it.

## Step 4 — Run a full investigation

### 4a. Restart the Agent K app

The app reads `.env` at startup. If it was already running, stop and restart
it so it picks up the new `SIGNOZ_API_KEY`:

```powershell
# Stop the current app
Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue |
  Select-Object -First 1 | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }

# Start fresh
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```

### 4b. Generate some telemetry (so the investigation has data to find)

```powershell
$body = '{"question":"How do I reset my password?"}'
curl.exe -s -X POST http://localhost:8000/ask -H "Content-Type: application/json" -d $body --max-time 30
```

### 4c. Fire the webhook to trigger an investigation

```powershell
$payload = @{
  receiver = "agent-k"
  status = "firing"
  alerts = @(
    @{
      status = "firing"
      labels = @{ alertname = "HighErrorRate"; service = "agent-k-rag-service"; severity = "critical" }
      annotations = @{ summary = "Error rate above SLO threshold"; burn_rate = "2.5" }
      startsAt = (Get-Date -Format "o")
      fingerprint = "demo-incident-001"
    }
  )
  groupLabels = @{ alertname = "HighErrorRate" }
  commonLabels = @{ service = "agent-k-rag-service" }
  commonAnnotations = @{}
  version = "4"
  groupKey = "{}:{alertname=HighErrorRate}"
} | ConvertTo-Json -Depth 6

curl.exe -s -X POST http://localhost:8000/alerts/webhook -H "Content-Type: application/json" -d $payload
```

Expected immediate response: `{"received":1}`

### 4d. Wait for the investigation to complete (~30-60 seconds)

The investigation runs in the background. It will:
1. Query SigNoz via MCP for evidence (traces, logs, metrics)
2. Form an LLM hypothesis via Groq
3. Run the Law 2 policy gate
4. Reach a terminal `REPORTED` or `ESCALATED` state

### 4e. Check the result

Open http://localhost:8000/report in a browser.

A **successful** investigation shows:
- **Outcome**: "Action denied by policy" or "Rollback executed" (not "Needs human")
- **Final state**: `reported` (not `escalated`)
- **SigNoz queries**: >0
- **Query failures**: 0
- **Tokens used**: >0
- **Evidence table**: real SigNoz queries with clickable "Open in SigNoz" links
- **Policy decision**: 6 checks with pass/fail verdicts

An **unsuccessful** investigation (MCP not working) shows:
- **Outcome**: "Needs human"
- **Final state**: `escalated`
- **Query failures**: 5 (all queries failed)
- **Tokens used**: 0
- **No evidence table**

## Step 5 — Refresh the JWT before a demo

The JWT expires every 30 minutes. Before demoing:

1. **Reload the SigNoz UI page** in the browser (http://localhost:8080) —
   this triggers a token refresh via the refresh token in localStorage.

2. **Extract the new JWT** from the browser console:
   ```javascript
   localStorage.getItem('AUTH_TOKEN')
   ```

3. **Update `.env`** with the new JWT:
   ```
   SIGNOZ_API_KEY="<new JWT>"
   ```

4. **Restart the app**:
   ```powershell
   Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue |
     Select-Object -First 1 | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
   Start-Sleep -Seconds 2
   .\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
   ```

5. **Verify** with a single MCP query (Step 3b) before demoing.

## Troubleshooting

### `Configuration validation failed: SIGNOZ_API_KEY is required for stdio mode`

The MCP server didn't receive the API key. Check:
- `.env` has `SIGNOZ_API_KEY="..."` (with quotes)
- The app/probe script is running from the project root (so `load_dotenv()` finds `.env`)
- Run `python -c "from dotenv import dotenv_values; print(dotenv_values('.env')['SIGNOZ_API_KEY'])"` to verify

### `401: unauthenticated` from the MCP server

The JWT has expired. Refresh it (Step 5) or the auth header patch wasn't
applied (Step 1c). Verify the patch by checking the binary was rebuilt after
patching.

### `Connection closed` during `session.initialize()`

The MCP server binary crashed on startup. Run it directly to see the error:
```powershell
$env:SIGNOZ_URL = "http://localhost:8080"
$env:SIGNOZ_API_KEY = "test"
$env:TRANSPORT_MODE = "stdio"
.\signoz-mcp-server.exe
```

### Investigation shows "Needs human" with 5 query failures

The MCP server is connecting but the queries are failing. Check:
1. The JWT is valid (not expired) — Step 5
2. The auth header patch is applied — Step 1c
3. Run the probe (Step 3b) to see the actual error message

### `signoz-mcp-server.exe` not found

The binary isn't in the project root or isn't on PATH. Either:
- Copy it to `f:\Hackathon ideas\Agent-K\signoz-mcp-server.exe` (Step 1e)
- Or set `SIGNOZ_MCP_COMMAND` to the full absolute path in `.env`

## What the MCP tool names are (reference)

Agent K's `app/investigation.py` uses these tool names (lines 92-94):

| Constant | Tool name | Purpose |
|---|---|---|
| `SIGNOZ_TRACES_TOOL` | `signoz_search_traces` | Raw span search |
| `SIGNOZ_LOGS_TOOL` | `signoz_search_logs` | Log search |
| `SIGNOZ_TRACE_STATS_TOOL` | `signoz_aggregate_traces` | Trace aggregation (deployment markers, latency metrics) |

These match the real MCP server's tool inventory — no code changes needed.

## Files modified by this setup

| File | Change |
|---|---|
| `signoz-mcp-server.exe` | New — built from source in WSL |
| `.env` | `SIGNOZ_MCP_COMMAND`, `SIGNOZ_URL`, `SIGNOZ_API_KEY` set |

No source code in `app/` is modified — the tool names were already correct.
