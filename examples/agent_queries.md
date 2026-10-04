# Example agent queries and expected tool calls

| User request | Tool call |
| --- | --- |
| Show me all unresolved high-priority tickets. | `list_tickets(status="unresolved", priority="high")` |
| Find tickets related to failed payments. | `search_tickets(query="failed payments")` |
| Find unresolved high-priority tickets about failed payments. | `search_tickets(query="failed payments", status="unresolved", priority="high")` |
| Get the details of ticket 12345. | `get_ticket(ticket_id=12345)` |
| Show me tickets created in the last 7 days. | `list_tickets(created_after="<today − 7 days>")` |
| Find all open tickets with high priority. | `list_tickets(status="open", priority="high")` |
| Which tickets mention refund failures? | `search_tickets(query="refund failures")` |

## Handling results

- If `has_more` is true, fetch `page=2` before claiming you have seen everything.
- If `truncated` is true on a search, say the result may be incomplete and offer to narrow by status or priority.
- On `{"success": false, ...}`, report the error `message` to the user; do not guess at ticket data.

## Requests the connector must refuse

"Close ticket 12345", "raise this to urgent", "reply to the customer", "refund this order" — there is no tool for
these; the agent should explain that the connector is read-only.
