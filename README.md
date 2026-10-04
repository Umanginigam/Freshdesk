# Freshdesk Agent Connector for Agent Studio

A production-oriented, read-only connector that enables an AI agent to securely access and retrieve Freshdesk support data through structured tools.

The connector provides authenticated access to tickets and exposes agent-friendly primitives for searching, listing, and retrieving ticket details. It includes authentication, pagination, rate-limit handling, retries, validation, error handling, and an MCP-compatible tool interface.

---

## 1. Overview

### Problem

Merchant support teams often need to manually search their support platform to answer questions such as:

* Which high-priority tickets are currently unresolved?
* What tickets are related to failed payments?
* What is the status of a specific ticket?
* Which tickets were created recently?
* Which customers have multiple unresolved issues?

An AI agent can make this workflow significantly faster if it can safely access the merchant's support system.

### Solution

This project implements a private Freshdesk connector that allows an Agent Studio-style agent to retrieve support information through structured tools.

The connector focuses on **read-only access** to minimize the risk of unintended changes to merchant data.

### Example

```text
User
 │
 │ "Show me unresolved high-priority tickets
 │  related to failed payments"
 ▼
AI Agent
 │
 │ search_tickets(...)
 ▼
Freshdesk Connector
 │
 ├── Authentication
 ├── Validation
 ├── Rate-limit handling
 ├── Retry handling
 └── Response normalization
 │
 ▼
Freshdesk API
 │
 ▼
Structured ticket results
 │
 ▼
AI Agent
 │
 ▼
Human-readable response
```

---

## 2. Key Capabilities

The connector supports:

* Secure Freshdesk authentication
* Ticket listing
* Ticket retrieval by ID
* Ticket search
* Filtering by status and priority
* Date-based filtering
* Pagination
* Rate-limit handling
* Retry with exponential backoff
* API timeout handling
* Structured response validation
* Normalized agent-friendly responses
* MCP-compatible tool definitions
* Read-only access boundaries
* Automated tests

---

## 3. Agent Tools

The connector exposes the following tools.

### `search_tickets`

Search tickets using a natural or structured query.

```text
search_tickets(
    query,
    status=None,
    priority=None,
    page=1,
    limit=20
)
```

Example:

```text
search_tickets(
    query="failed payment",
    status="open",
    priority="high"
)
```

---

### `list_tickets`

Retrieve tickets using filters.

```text
list_tickets(
    status=None,
    priority=None,
    created_after=None,
    created_before=None,
    page=1,
    limit=20
)
```

Example:

```text
list_tickets(
    status="open",
    priority="high"
)
```

---

### `get_ticket`

Retrieve a specific ticket.

```text
get_ticket(
    ticket_id
)
```

Example:

```text
get_ticket(
    ticket_id=12345
)
```

---

## 4. What the Agent Can Do

The agent can:

* Search support tickets
* Retrieve individual ticket details
* List tickets using filters
* Identify high-priority tickets
* Identify unresolved tickets
* Filter tickets by date
* Search for tickets related to a specific issue
* Summarize retrieved ticket information
* Answer questions using retrieved Freshdesk data

### Example queries

```text
"Show me all unresolved high-priority tickets."

"Find tickets related to failed payments."

"Get the details of ticket 12345."

"Show me tickets created in the last 7 days."

"Find all open tickets with high priority."

"Which tickets mention refund failures?"
```

---

## 5. What the Agent Cannot Do

The connector intentionally provides **read-only access**.

The agent cannot:

* Create tickets
* Update tickets
* Delete tickets
* Close tickets
* Change ticket priority
* Modify customer information
* Trigger refunds
* Send customer messages
* Execute arbitrary Freshdesk API calls

This boundary is intentional because autonomous mutation of merchant support data introduces additional security, authorization, and business-risk requirements.

---

# 6. Architecture

```text
                         ┌──────────────────────┐
                         │       User           │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │      AI Agent        │
                         │                      │
                         │ Tool Selection       │
                         │ Reasoning            │
                         │ Response Generation  │
                         └──────────┬───────────┘
                                    │
                              MCP / Tools
                                    │
             ┌──────────────────────┼──────────────────────┐
             │                      │                      │
             ▼                      ▼                      ▼
      search_tickets          list_tickets           get_ticket
             │                      │                      │
             └──────────────────────┼──────────────────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Freshdesk Connector  │
                         │                      │
                         │ Auth                 │
                         │ Validation           │
                         │ Rate Limiting        │
                         │ Retry Logic           │
                         │ Error Handling       │
                         │ Response Mapping     │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │    Freshdesk API     │
                         └──────────────────────┘
```

---

# 7. Project Structure

```text
freshdesk-agent-connector/
│
├── README.md
├── architecture.md
├── requirements.txt
├── .env.example
├── .gitignore
│
├── app/
│   ├── main.py
│   │
│   ├── auth/
│   │   └── api_key.py
│   │
│   ├── freshdesk/
│   │   ├── client.py
│   │   ├── tickets.py
│   │   └── errors.py
│   │
│   ├── tools/
│   │   ├── search_tickets.py
│   │   ├── list_tickets.py
│   │   ├── get_ticket.py
│   │   └── mcp_server.py
│   │
│   ├── middleware/
│   │   ├── rate_limiter.py
│   │   └── retry.py
│   │
│   └── models/
│       └── ticket.py
│
├── tests/
│   ├── test_auth.py
│   ├── test_tickets.py
│   ├── test_search.py
│   ├── test_rate_limit.py
│   └── test_errors.py
│
├── examples/
│   └── agent_queries.md
│
└── docs/
    ├── security.md
    ├── limitations.md
    └── evaluation.md
```

---

# 8. Authentication

The connector uses Freshdesk API-key authentication.

Credentials are supplied through environment variables and are never hardcoded.

Example:

```env
FRESHDESK_DOMAIN=your-domain
FRESHDESK_API_KEY=your-api-key
```

A template is provided in:

```text
.env.example
```

No real credentials are included in this repository.

---

# 9. Rate Limiting

The connector handles Freshdesk API rate limits rather than allowing repeated requests to fail uncontrolled.

When a rate-limit response is received:

1. Detect the rate-limit response.
2. Read the available retry information when provided.
3. Wait before retrying.
4. Apply exponential backoff where appropriate.
5. Stop after a maximum retry count.
6. Return a structured error if the request still cannot be completed.

Example strategy:

```text
Request
   │
   ▼
API
   │
   ├── Success ──────────────► Return result
   │
   └── Rate limited
            │
            ▼
       Wait / Backoff
            │
            ▼
          Retry
            │
            ├── Success ─────► Return result
            │
            └── Failure ─────► Structured error
```

---

# 10. Error Handling

The connector normalizes external API failures into predictable application-level errors.

Handled cases include:

* Invalid authentication
* Unauthorized access
* Ticket not found
* Invalid request parameters
* Rate limiting
* API timeout
* Network errors
* Unexpected API responses
* Malformed response data

The agent should receive a useful error instead of raw API internals.

Example:

```json
{
  "success": false,
  "error": {
    "type": "TICKET_NOT_FOUND",
    "message": "The requested ticket could not be found."
  }
}
```

---

# 11. Pagination

Freshdesk may return results across multiple pages.

The connector therefore exposes pagination explicitly rather than loading an unbounded number of tickets into the agent context.

Example:

```text
page=1
limit=20
```

The agent can request additional pages when required.

This also helps control:

* API usage
* latency
* memory
* LLM context size
* token consumption

---

# 12. Security and Guardrails

Security is treated as a first-class concern.

### Credential protection

* Credentials are stored in environment variables.
* Secrets are excluded from Git.
* `.env` is included in `.gitignore`.
* No real customer data is committed.

### Tool-level restrictions

Only explicitly defined Freshdesk operations are exposed to the agent.

The agent cannot construct arbitrary API requests.

### Read-only design

The connector does not expose mutation endpoints.

### Input validation

Tool parameters are validated before requests are sent to Freshdesk.

### Data minimization

Only the fields required by the agent are returned where possible.

---

# 13. MCP Tool Specification

The connector exposes the following tools to the agent.

```json
{
  "name": "get_ticket",
  "description": "Retrieve a Freshdesk ticket by ID",
  "inputSchema": {
    "type": "object",
    "properties": {
      "ticket_id": {
        "type": "integer",
        "description": "Freshdesk ticket ID"
      }
    },
    "required": ["ticket_id"]
  }
}
```

Similar schemas are provided for:

```text
search_tickets
list_tickets
```

The tool interface intentionally provides a small, explicit capability surface rather than exposing the entire Freshdesk API.

---

# 14. Evaluation

The connector is evaluated across several dimensions.

| Area           | Test                          |
| -------------- | ----------------------------- |
| Authentication | Valid and invalid credentials |
| Retrieval      | Get ticket by ID              |
| Search         | Search by keyword             |
| Filtering      | Status/priority filters       |
| Pagination     | Multiple result pages         |
| Errors         | Invalid ticket ID             |
| Rate limiting  | Simulated rate-limit response |
| Timeout        | Simulated API timeout         |
| Validation     | Invalid tool parameters       |
| Security       | Mutation attempts rejected    |

The goal is to verify not only that the happy path works, but also that the connector behaves predictably under failure conditions.

---

# 15. Example Agent Workflow

### User

```text
Find all unresolved high-priority tickets related to failed payments.
```

### Agent

```text
1. Understand request
2. Select search_tickets
3. Apply:
   - query = "failed payments"
   - status = "open"
   - priority = "high"
4. Call connector
5. Handle pagination if required
6. Validate returned data
7. Summarize results
```

### Result

```text
Found 7 unresolved high-priority tickets related to failed payments.

3 tickets are older than 48 hours.
2 tickets are from the same customer.
The oldest ticket was created 4 days ago.
```

---

# 16. Setup

## Prerequisites

* Python 3.10+
* Freshdesk account
* Freshdesk API key

Clone the repository:

```bash
git clone <repository-url>
cd freshdesk-agent-connector
```

Create a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create environment variables:

```bash
cp .env.example .env
```

Add your Freshdesk credentials to `.env`.

---

# 17. Running the Connector

Start the application:

```bash
python -m app.main
```

The MCP/tool server will then expose the configured tools to the agent.

Detailed integration instructions are available in:

```text
docs/
```

---

# 18. Running Tests

Run:

```bash
pytest -v
```

The test suite covers:

* Authentication
* Ticket retrieval
* Search
* Filtering
* Pagination
* Error handling
* Rate limiting
* Input validation

---

# 19. Limitations

This implementation intentionally has a limited scope.

### Current limitations

* Read-only Freshdesk access
* Limited set of supported ticket operations
* No ticket mutation
* No customer-message sending
* No automatic business actions
* Pagination is bounded to prevent excessive API/context usage
* Production deployment would require stronger secret management and observability

These limitations are intentional for the assignment and reduce the risk of an AI agent taking unintended actions.

---

# 20. Production Considerations

For a production deployment, I would additionally consider:

### Security

* OAuth where appropriate
* Secret manager integration
* Fine-grained permissions
* Tenant isolation
* Audit logging

### Reliability

* Circuit breakers
* Distributed rate limiting
* Request tracing
* Dead-letter handling for asynchronous workflows

### Observability

* Tool-call latency
* API error rate
* Rate-limit frequency
* Agent tool-selection accuracy
* Failed tool calls
* Token consumption

### Agent quality

* Tool-selection evaluation
* Retrieval accuracy
* Groundedness checks
* Regression test suite
* Human feedback loop

---

# 21. What the Agent Can and Cannot Do

| Capability                  | Supported |
| --------------------------- | --------: |
| Search tickets              |         ✅ |
| List tickets                |         ✅ |
| Get ticket                  |         ✅ |
| Filter tickets              |         ✅ |
| Pagination                  |         ✅ |
| Summarize retrieved tickets |         ✅ |
| Create ticket               |         ❌ |
| Update ticket               |         ❌ |
| Delete ticket               |         ❌ |
| Close ticket                |         ❌ |
| Send customer message       |         ❌ |
| Trigger refund              |         ❌ |

The connector is deliberately designed around **least privilege**.

---

# 22. Future Improvements

If this were deployed beyond the assignment, I would consider:

1. OAuth-based authentication
2. Multi-tenant credential isolation
3. Fine-grained merchant permissions
4. Additional Freshdesk resources
5. Webhook-based event ingestion
6. Semantic ticket search
7. Conversation summarization
8. Human approval before sensitive actions
9. Distributed rate limiting
10. Production observability and audit trails

---

# 23. Assignment Context

This project was developed as part of the **Forward-Deployed Engineer, Agent Studio** application process.

The implementation focuses on demonstrating:

* Production engineering
* API integration
* Agent/tool design
* Merchant workflow understanding
* Reliability
* Security
* Guardrails
* Customer-oriented problem solving

The design intentionally prioritizes a small, reliable and explainable tool surface over exposing the complete Freshdesk API.

---

# 24. Author

**Umangi Nigam**

AI / LLM Engineer
Bangalore, India

Experience with:

* LLM applications
* RAG
* LangChain
* LangGraph
* Agent workflows
* Python
* FastAPI
* Vector databases
* API integrations
* Production AI systems
