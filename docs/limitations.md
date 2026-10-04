# Limitations

- **Read-only.** No create/update/delete/close/reply/refund operations, by design.
- **Search window is 300 results.** Freshdesk search returns at most 10 pages of 30. Narrow with status, priority or dates.
- **Keyword search is a bounded scan.** Keywords are matched in the connector over at most 300 candidates, not by a
  full-text index. `truncated: true` signals possible missed matches. Matching is substring-based with light stemming
  (`failed payments` ≈ `payment failure`); it is not semantic.
- **Date filters are date-granular** (`YYYY-MM-DD`), applied as strict `>` / `<` by Freshdesk's search syntax.
- **Single tenant.** One Freshdesk account per process, configured by environment variables.
- **In-process rate limiting.** The sliding window is per process; running several instances against one account needs a shared limiter.
- **Custom statuses** appear as `status_<id>` and cannot be targeted by the status filter.
- **Live-verified** against a Freshdesk trial account for get, list, search, filters and not-found errors. Rate-limit and timeout behaviour is covered by mocked tests only.
