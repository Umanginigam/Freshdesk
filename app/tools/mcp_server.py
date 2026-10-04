"""MCP server exposing exactly three read-only tools."""

import logging
from typing import Any, Literal, Optional

from app.auth.api_key import Credentials
from app.config import Settings
from app.freshdesk.client import FreshdeskClient
from app.freshdesk.errors import ConnectorError
from app.freshdesk.tickets import DEFAULT_LIMIT, MAX_LIMIT, TicketService
from app.tools import get_ticket, list_tickets, search_tickets

logger = logging.getLogger(__name__)

StatusFilter = Literal["open", "pending", "resolved", "closed", "unresolved"]
PriorityFilter = Literal["low", "medium", "high", "urgent"]


def build_server(service: Optional[TicketService] = None):
    try:  # mcp >= 2: FastMCP was renamed to MCPServer
        from mcp.server.mcpserver import MCPServer as ServerClass
    except ImportError:  # mcp 1.x
        from mcp.server.fastmcp import FastMCP as ServerClass

    mcp = ServerClass(
        "freshdesk-connector",
        instructions=(
            "Read-only access to Freshdesk support tickets. Use search_tickets for keyword "
            "questions, list_tickets for filter/date questions, get_ticket for a known ID."
        ),
    )
    holder: dict[str, Optional[TicketService]] = {"service": service}

    def call(run, **kwargs) -> dict[str, Any]:
        # Build the Freshdesk client lazily so a config problem is reported as a tool error.
        if holder["service"] is None:
            try:
                holder["service"] = TicketService(
                    FreshdeskClient(Credentials.from_env(), Settings.from_env())
                )
            except ConnectorError as exc:
                return exc.to_dict()
        return run(holder["service"], **kwargs)

    @mcp.tool(name=get_ticket.NAME, description=get_ticket.DESCRIPTION)
    def get_ticket_tool(ticket_id: int) -> dict[str, Any]:
        return call(get_ticket.run, ticket_id=ticket_id)

    @mcp.tool(name=list_tickets.NAME, description=list_tickets.DESCRIPTION)
    def list_tickets_tool(
        status: Optional[StatusFilter] = None,
        priority: Optional[PriorityFilter] = None,
        created_after: Optional[str] = None,
        created_before: Optional[str] = None,
        page: int = 1,
        limit: int = DEFAULT_LIMIT,
    ) -> dict[str, Any]:
        return call(
            list_tickets.run,
            status=status,
            priority=priority,
            created_after=created_after,
            created_before=created_before,
            page=page,
            limit=limit,
        )

    @mcp.tool(name=search_tickets.NAME, description=search_tickets.DESCRIPTION)
    def search_tickets_tool(
        query: str,
        status: Optional[StatusFilter] = None,
        priority: Optional[PriorityFilter] = None,
        page: int = 1,
        limit: int = DEFAULT_LIMIT,
    ) -> dict[str, Any]:
        return call(
            search_tickets.run, query=query, status=status, priority=priority, page=page, limit=limit
        )

    return mcp
