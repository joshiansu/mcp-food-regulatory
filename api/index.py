"""
Vercel entrypoint for mcp-food-regulatory.

Single ASGI dispatcher:
  GET /        → serves index.html (landing page)
  POST/DELETE /mcp → FastMCP streamable-http transport (stateless_http=True for serverless)
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from starlette.responses import HTMLResponse  # noqa: E402
from mcp_food_regulatory.server import mcp   # noqa: E402

_HTML_PATH = os.path.join(os.path.dirname(__file__), "..", "index.html")
_mcp_app = mcp.http_app(stateless_http=True)


class _App:
    """Routes GET / to the landing page; everything else to the MCP ASGI app."""

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            await _mcp_app(scope, receive, send)
            return
        if (
            scope["type"] == "http"
            and scope.get("path") == "/"
            and scope.get("method") == "GET"
        ):
            with open(_HTML_PATH, encoding="utf-8") as f:
                html = f.read()
            await HTMLResponse(html)(scope, receive, send)
            return
        await _mcp_app(scope, receive, send)


app = _App()
