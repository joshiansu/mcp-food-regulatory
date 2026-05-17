"""
Vercel entrypoint for mcp-food-regulatory.

Exposes the FastMCP Starlette ASGI app at /mcp (streamable-http transport).
stateless_http=True is required for serverless -- no session persistence between invocations.
"""

import sys
import os

# Make the src/ package importable without installation
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from mcp_food_regulatory.server import mcp  # noqa: E402

app = mcp.http_app(stateless_http=True)
