# Getting the API keys Agent K needs

Everything here was verified against **the SigNoz actually running on this machine**
(v0.134.0, EE build) on 2026-07-25 — not against generic docs. Menu names in older
SigNoz guides are wrong for this version; see the warning in §1.

You need three values in `.env`. Two are real credentials you generate; one you
generate locally with a shell command.

| Value | Where from | Blocks |
|---|---|---|
| `SIGNOZ_API_KEY` | SigNoz UI (§1) | Everything — MCP evidence, alert rule, live run, dashboards |
| `GROQ_API_KEY` | console.groq.com (§2) | Any real investigation, HV-1 |
| `DEPLOYER_TOKEN` | one shell command (§3) | The rollback sidecar |

---

## 1. `SIGNOZ_API_KEY`

> **The "API Keys" page is deprecated in v0.134.0.** `/settings/api-keys` and
> `/settings/access-tokens` both now redirect to **Service Accounts**, and the UI
> shows an API-keys deprecation banner. Any guide telling you to go to
> "Settings → API Keys" is out of date for this build. Use Service Accounts.

**Direct link:** http://localhost:8080/settings/service-accounts

Or navigate: SigNoz UI → gear icon (Settings) → **Identity & Access** → **Service Accounts**

Steps:

1. Open the link above. Log in with the account you registered when the stack was
   first set up (the `curl .../api/v1/register` step in
   [SIGNOZ-RUNBOOK.md](SIGNOZ-RUNBOOK.md#15-required-first-run-setup-do-this-immediately-after-cast-before-anything-else)).
2. Create a service account, then create a **token** on it.
3. **Give it the `ADMIN` role.** Not Editor, not Viewer.
   - Read-only would be enough for querying traces/logs/metrics, but Agent K also
     needs to *create* the alert rule, the webhook notification channel, and the
     dashboards through the MCP server. Those are admin-scoped writes, and a
     Viewer token fails them with a 403 that surfaces only at the point of use.
4. **Copy the token immediately.** It is shown once. If you lose it, delete it and
   make a new one — there is no way to read it back.

Then add it, replacing the placeholder:

```bash
cd /Users/ayushbharadva/dev/personal/Agent-K
{
  echo 'SIGNOZ_URL=http://localhost:8080'
  echo 'SIGNOZ_MCP_COMMAND=./signoz-mcp-server'
  echo 'SIGNOZ_API_KEY=PASTE_YOUR_SIGNOZ_TOKEN_HERE'
} >> .env
```

> Related, worth knowing: this build also has a built-in **MCP Server** settings page
> at http://localhost:8080/settings/mcp-server. We do not need it — Agent K runs the
> `signoz-mcp-server` binary itself over stdio, which is what the locked spec
> requires — but that page is where SigNoz documents its own hosted MCP endpoint.

---

## 2. `GROQ_API_KEY`

**Direct link:** https://console.groq.com/keys

1. Sign in (Google/GitHub sign-in works; the free tier needs no card).
2. **Create API Key**, name it anything (`agent-k` is fine).
3. Copy it — like SigNoz, it is shown once.

```bash
cd /Users/ayushbharadva/dev/personal/Agent-K
echo 'GROQ_API_KEY=PASTE_YOUR_GROQ_KEY_HERE' >> .env
echo 'LLM_PROVIDER=groq' >> .env
```

Groq keys start with `gsk_`.

**Optional overflow provider** — only if Groq rate-limits during the 12 eval runs
(EVAL-02 names Cerebras as the overflow path):

```bash
echo 'CEREBRAS_API_KEY=PASTE_IF_YOU_HAVE_ONE' >> .env    # https://cloud.cerebras.ai
```

Switching provider later is one env var: `LLM_PROVIDER=cerebras`. Nothing else changes.

---

## 3. `DEPLOYER_TOKEN`

Not a third-party credential — it is a shared secret between Agent K and the rollback
sidecar, so you just generate a random one:

```bash
cd /Users/ayushbharadva/dev/personal/Agent-K
echo "DEPLOYER_TOKEN=$(openssl rand -hex 24)" >> .env
```

The sidecar refuses to serve `/rollback` at all without it (HTTP 503) — deliberately,
since it is the one container holding the Docker socket.

---

## 4. Also useful

```bash
cd /Users/ayushbharadva/dev/personal/Agent-K
echo "ADMIN_TOKEN=$(openssl rand -hex 16)" >> .env    # gates POST /admin/flags
```

Without it the failure-injection endpoint is open — fine on localhost, not otherwise.

---

## 5. Verify it all worked

Run these in order. Each one tells you something different.

**a. The keys are being read at all:**

```bash
.venv/bin/python -c "from dotenv import load_dotenv; import os; load_dotenv(); [print(f'{k:20} {\"SET\" if os.getenv(k) else \"*** MISSING ***\"}') for k in ('SIGNOZ_URL','SIGNOZ_API_KEY','SIGNOZ_MCP_COMMAND','GROQ_API_KEY','DEPLOYER_TOKEN')]"
```

**b. The SigNoz token is valid and the MCP server can use it** — this is the real test:

```bash
.venv/bin/python scripts/probe_signoz_mcp.py --list-tools
```

Expect ~41 tools printed, all named `signoz_*`. If you instead get
`SIGNOZ_API_KEY is required for stdio mode`, the key is not reaching the process —
check `.env` is in the repo root and has no quotes around the value.

**c. Real telemetry actually comes back:**

```bash
.venv/bin/python scripts/probe_signoz_mcp.py signoz_search_traces '{"service": "agent-k-rag-service", "limit": 2}'
```

**d. The Groq key works:**

```bash
.venv/bin/python -c "from dotenv import load_dotenv; load_dotenv(); from app.llm import generate; print(generate('Say OK and nothing else.').answer)"
```

---

## 6. Safety notes

- `.env` is gitignored (`**/.env*` in [.gitignore](.gitignore)) — it will not be
  committed. Do not paste real keys into `.env.example`, any `.md` file, a commit
  message, or the submission blog.
- If a key does leak into a commit, **revoke it at the provider first**, then worry
  about history. Revoking is instant; rewriting history is not.
- These are all free-tier credentials, but the SigNoz service-account token is
  ADMIN-scoped on your observability stack — treat it like a password.
