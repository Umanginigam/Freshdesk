# Architecture

## Layers

```text
MCP client (agent)
      │  stdio
      ▼
app/tools/mcp_server.py     FastMCP server; registers exactly 3 tools
      │
app/tools/{get,list,search}_tickets.py   schema + run(); every outcome → {"success": ...}
      │
app/freshdesk/tickets.py    validation, query building, pagination, keyword matching
      │
app/freshdesk/client.py     GET-only, path allowlist, auth, HTTP→error mapping
   ├─ app/middleware/rate_limiter.py   sliding window, client-side
   └─ app/middleware/retry.py          429 / 5xx / timeout retry with backoff
      │  HTTPS
      ▼
Freshdesk API v2
```

Errors are `ConnectorError` subclasses (`app/freshdesk/errors.py`) with a stable `type`; the tool layer
converts them to `{"success": false, "error": {...}}`. Unknown exceptions become `INTERNAL_ERROR` with no details.

## Key decisions

**Search goes through `/search/tickets`.** Freshdesk's list endpoint cannot filter by status/priority and
defaults to the last 30 days. The search endpoint supports `status`, `priority` and `created_at` filters, so
`list_tickets` always uses it.

**Search API limits shape pagination.** It returns 30 results per page and at most 10 pages (300 results).
`list_tickets` maps the agent's `(page, limit)` onto those windows (at most two upstream calls per request) and
rejects windows beyond 300 with a hint to narrow the filters.

**Keyword search is done in the connector.** Freshdesk's search has no free-text operator. `search_tickets`
pushes status/priority down to Freshdesk, scans up to 300 candidates, and requires every keyword (lightly
stemmed) to appear in subject, description or tags. If more candidates existed than were scanned, the response
sets `truncated: true` so the agent can tell the user the result may be incomplete.

**Read-only is enforced twice.** The tool surface has no mutating tools, and the HTTP client independently
refuses any non-GET method and any path outside `/tickets/{id}` and `/search/tickets`.

**Retries.** 429 waits for `Retry-After` (capped at 30 s) or backs off 0.5 s, 1 s, 2 s…; 500/502/503/504 and
timeouts/transport errors back off the same way; all stop after `FRESHDESK_MAX_RETRIES`.

**Lazy client creation.** The MCP server starts even with missing credentials; the first tool call returns a
`CONFIGURATION_ERROR` instead of crashing the process.
