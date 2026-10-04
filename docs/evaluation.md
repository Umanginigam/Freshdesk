# Evaluation

All tests use `httpx.MockTransport`; none touch the network. Run with `pytest -v`.

| Area | Test file | What it checks |
| --- | --- | --- |
| Authentication | `test_auth.py` | Credentials from env, placeholder/missing rejection, domain validation, Basic auth header, 401 → `INVALID_CREDENTIALS` without retry |
| Retrieval | `test_tickets.py` | Get by ID, normalization, unknown status labels, description truncation |
| Filtering | `test_tickets.py` | status / priority / unresolved / date range → Freshdesk query |
| Pagination | `test_tickets.py` | `(page, limit)` → 30-per-page windows, `has_more`, 300-result cap |
| Search | `test_search.py` | Keyword matching across subject/description/tags, all-terms, ordering, local pagination, bounded scan + `truncated` |
| Errors | `test_errors.py` | 403, 404, 400/422, non-JSON, malformed ticket, bad search payload |
| Rate limiting | `test_rate_limit.py` | Retry-After, exponential backoff, cap, exhaustion, client-side limiter |
| Timeout / network | `test_errors.py` | Retry then `API_TIMEOUT` / `NETWORK_ERROR`; recovery after a transient timeout |
| Validation | `test_tickets.py`, `test_search.py` | Bad IDs, limits, pages, enums, dates, queries — rejected before any request |
| Security | `test_errors.py` | Non-GET methods and non-allowlisted paths rejected; exactly 3 MCP tools; no internal leakage |

## Next: agent-level evaluation

Tool-selection accuracy on `examples/agent_queries.md`, groundedness of summaries against returned tickets, and a
live smoke test against a Freshdesk sandbox account.
