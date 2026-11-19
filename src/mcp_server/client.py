"""FastMCP client demo for the SmartSpend expense tracker."""

import asyncio
from datetime import date

from fastmcp import Client

SERVER_URL = "http://127.0.0.1:8000/mcp"
client = Client(SERVER_URL)


async def run_demo() -> None:
    """Discover SmartSpend tools and demonstrate expense operations."""
    async with client:
        tools = await client.list_tools()
        print(f"Discovered {len(tools)} tools on the server:")
        for tool in tools:
            print(f" - {tool.name}: {tool.description}")

        today = date.today().isoformat()
        added = await client.call_tool(
            "add_expense",
            {
                "date": today,
                "amount": 12.50,
                "category": "food",
                "subcategory": "coffee_tea",
                "note": "SmartSpend client demo",
            },
        )
        print("Added expense:", added.data)

        expenses = await client.call_tool(
            "list_expenses",
            {"start_date": today, "end_date": today},
        )
        print("Today's expenses:", expenses.data)

        summary = await client.call_tool(
            "summarize",
            {"start_date": today, "end_date": today},
        )
        print("Today's totals by category:", summary.data)

        categories = await client.read_resource("expense://categories")
        print("Expense categories:", categories)


def main() -> None:
    """Run the asynchronous SmartSpend client demo."""
    try:
        asyncio.run(run_demo())
    except Exception as exc:
        print(f"\n[Error] Unable to communicate with SmartSpend MCP server: {exc}")
        print("Start it first with: uv run smartspend-server\n")


if __name__ == "__main__":
    main()
