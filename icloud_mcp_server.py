#!/usr/bin/env python3
"""MCP server exposing iCloud Calendar tools.

Imports icloud_calendar.py directly (no HTTP hop through icloud_bridge.py),
so it needs the same config.json / secret-file credentials as the bridge.
Runs as its own process, on its own port, separate from icloud_bridge.py.
"""

import os

from mcp.server.fastmcp import FastMCP

import icloud_calendar as calendar

mcp = FastMCP("icloud-calendar")


@mcp.tool()
def list_calendars() -> dict:
    """List configured iCloud calendars and their calendar IDs."""
    return calendar.list_calendars()


@mcp.tool()
def list_events(days: int = 7, limit: int = 20) -> dict:
    """List upcoming events across all calendars.

    days: how many days ahead to look (1-60, default 7)
    limit: max events to return (1-200, default 20)
    """
    days = max(1, min(int(days), 60))
    limit = max(1, min(int(limit), 200))
    return calendar.get_events_list(days=days, limit=limit)


@mcp.tool()
def create_event(
    calendar_name: str,
    summary: str,
    start: str,
    end: str = "",
    description: str = "",
    all_day: bool = False,
) -> dict:
    """Create a calendar event.

    calendar_name: one of the names returned by list_calendars
    summary: event title
    start: ISO 8601 datetime (e.g. 2026-08-12T14:00:00), or YYYY-MM-DD if all_day
    end: optional ISO 8601 datetime/date; defaults to 30 min after start
         (or the day after start for all-day events); end date is exclusive
    all_day: set True for all-day events
    """
    return calendar.create_event(calendar_name, summary, start, end or None, description, all_day)


@mcp.tool()
def delete_event(identifier: str, calendar_name: str = "") -> dict:
    """Delete an event by title or UID, optionally scoped to one calendar."""
    return calendar.cmd_delete(identifier, calendar_name or None)


if __name__ == "__main__":
    mcp.settings.host = os.environ.get("ICLOUD_MCP_HOST", "0.0.0.0")
    mcp.settings.port = int(os.environ.get("ICLOUD_MCP_PORT", "8094"))

    # FastMCP's DNS-rebinding guard only allows localhost by default; a client
    # connecting via LAN IP or a tunnel hostname needs those added explicitly.
    default_hosts = "192.168.0.201:8094,icloud-calendar-mcp-internal.drewhobick.com,icloud-calendar-mcp.drewhobick.com"
    hosts_raw = os.environ.get("ICLOUD_MCP_ALLOWED_HOSTS", default_hosts)
    extra_hosts = [h.strip() for h in hosts_raw.split(",") if h.strip()]
    if extra_hosts:
        mcp.settings.transport_security.allowed_hosts.extend(extra_hosts)
        mcp.settings.transport_security.allowed_origins.extend(f"https://{h}" for h in extra_hosts)
        mcp.settings.transport_security.allowed_origins.extend(f"http://{h}" for h in extra_hosts)

    mcp.run(transport="streamable-http")
