from fastapi import FastAPI, Request
from fastmcp import FastMCP
from typing import Optional, Dict, Any
import json

from .auth import APIKeyMiddleware
from . import jules_client

# Initialize FastMCP Server
mcp = FastMCP("Jules MCP")

def wrap_response(resp: Dict[str, Any]) -> str:
    """
    FastMCP tools currently expect string returns (or complex MCP objects).
    We JSON-serialize our dict structure as requested.
    """
    return json.dumps(resp)

# ---------------------------------------------------------
# Tool Definitions
# ---------------------------------------------------------

@mcp.tool()
async def jules_list_sources() -> str:
    """List Jules sources."""
    resp = await jules_client.list_sources()
    return wrap_response(resp)

@mcp.tool()
async def jules_get_source(name: str) -> str:
    """Get a Jules source by name."""
    resp = await jules_client.get_source(name)
    return wrap_response(resp)

@mcp.tool()
async def jules_create_session(
    source: str,
    startingBranch: str,
    prompt: str,
    title: str = "",
    requirePlanApproval: bool = True,
    automationMode: Optional[str] = None
) -> str:
    """Create a new Jules session."""
    resp = await jules_client.create_session(
        source=source,
        starting_branch=startingBranch,
        prompt=prompt,
        title=title,
        require_plan_approval=requirePlanApproval,
        automation_mode=automationMode
    )
    return wrap_response(resp)

@mcp.tool()
async def jules_list_sessions(pageSize: int = 50, pageToken: str = "") -> str:
    """List Jules sessions."""
    resp = await jules_client.list_sessions(page_size=pageSize, page_token=pageToken)
    return wrap_response(resp)

@mcp.tool()
async def jules_get_session(session: str) -> str:
    """Get a Jules session by name."""
    resp = await jules_client.get_session(session)
    return wrap_response(resp)

@mcp.tool()
async def jules_send_message(session: str, prompt: str) -> str:
    """Send a message to a Jules session."""
    resp = await jules_client.send_message(session, prompt)
    return wrap_response(resp)

@mcp.tool()
async def jules_approve_plan(session: str) -> str:
    """Approve a Jules plan. Only explicitly call this when the user approves."""
    resp = await jules_client.approve_plan(session)
    return wrap_response(resp)

@mcp.tool()
async def jules_list_activities(session: str, pageSize: int = 50, pageToken: str = "") -> str:
    """List activities for a Jules session."""
    resp = await jules_client.list_activities(session, page_size=pageSize, page_token=pageToken)
    return wrap_response(resp)

@mcp.tool()
async def jules_get_activity(activity: str) -> str:
    """Get a Jules activity by name."""
    resp = await jules_client.get_activity(activity)
    return wrap_response(resp)

@mcp.tool()
async def jules_wait_for_activity(
    session: str,
    matchText: str = "",
    timeoutSeconds: int = 600,
    pollIntervalSeconds: int = 10,
    pageSize: int = 50
) -> str:
    """Poll session/activities until complete, timeout, or match_text found."""
    resp = await jules_client.wait_for_activity(
        session=session,
        match_text=matchText,
        timeout_seconds=timeoutSeconds,
        poll_interval_seconds=pollIntervalSeconds,
        page_size=pageSize
    )
    return wrap_response(resp)

@mcp.tool()
async def jules_cancel_session(session: str) -> str:
    """Cancel a Jules session."""
    return json.dumps({
        "supported": False,
        "message": "The public Jules API does not expose a documented cancel/stop endpoint in this implementation."
    })


# ---------------------------------------------------------
# FastAPI Application setup
# ---------------------------------------------------------

app = FastAPI(title="Jules MCP Server")

# Add authentication middleware
app.add_middleware(APIKeyMiddleware)

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"ok": True}

# Mount FastMCP HTTP app on standard paths. The fastmcp `.http_app()` method
# returns a Starlette ASGI app which exposes its own SSE routes at /sse and /messages.
# Since the goal is `/mcp` and `/sse`, we mount the mcp.http_app().
fastmcp_app = mcp.http_app()
app.mount("/mcp", fastmcp_app)
app.mount("/sse", fastmcp_app)
