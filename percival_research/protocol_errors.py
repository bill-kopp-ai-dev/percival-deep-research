"""Adapt the server's legacy safe error strings at its MCP boundary only."""

from fastmcp.server.middleware import Middleware
from mcp.types import TextContent


class ProtocolErrors(Middleware):
    async def on_call_tool(self, context, call_next):
        result = await call_next(context)
        # These are this server's established handler error responses, not a
        # client heuristic over arbitrary upstream MCP content. Direct Python
        # callers keep their str contract; wire callers get proper isError.
        if result.content and isinstance(result.content[0], TextContent):
            if result.content[0].text.startswith("Error:"):
                result.is_error = True
        return result
