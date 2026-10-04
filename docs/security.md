# Security

| Control | Where |
| --- | --- |
| Secrets only from environment; `.env` git-ignored; key hidden from `repr()` | `app/auth/api_key.py`, `.gitignore` |
| Domain restricted to a plain subdomain, so requests can only reach `*.freshdesk.com` | `normalize_domain` |
| Placeholder credentials from `.env.example` are rejected | `Credentials.__post_init__` |
| Only GET, only `/tickets/{id}` and `/search/tickets` | `app/freshdesk/client.py` |
| No mutating tool exists; the agent cannot build arbitrary API calls | `app/tools/mcp_server.py` |
| All tool inputs validated before any request; enum-restricted status/priority | `app/freshdesk/tickets.py` |
| Search query values are generated from validated enums and parsed dates, never from raw agent text | `build_api_query` |
| Descriptions truncated to 500 chars; only needed fields returned | `app/models/ticket.py` |
| Errors normalized; unknown exceptions return no internals | `app/tools/common.py` |
| Logs go to stderr (stdout is the MCP channel) and never include credentials or ticket content | `app/main.py` |

Not covered (see `limitations.md`): per-user authorization, audit logging, tenant isolation, secret-manager integration.
Ticket text is untrusted customer input; an agent consuming it should treat it as data, not instructions.
