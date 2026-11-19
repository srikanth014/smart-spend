"""SmartSpend MCP server package.

An expense tracking MCP server with SQLite persistence, compatible with
FastMCP clients and LangChain agents.
"""

__version__ = "0.1.0"


def main() -> None:
    """Run the FastMCP server."""
    from mcp_server.server import main as server_main
    server_main()


__all__ = ["main", "__version__"]
