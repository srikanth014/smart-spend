"""FastMCP server exposing SmartSpend expense tracking tools."""

from pathlib import Path

from fastmcp import FastMCP
from mcp_server.database import add_expense as save_expense
from mcp_server.database import delete_expense as remove_expense
from mcp_server.database import get_expense as fetch_expense
from mcp_server.database import list_expenses as fetch_expenses
from mcp_server.database import summarize as summarize_expenses
from mcp_server.database import update_expense as revise_expense

mcp = FastMCP("SmartSpend")
CATEGORIES_PATH = Path(__file__).with_name("categories.json")


@mcp.tool()
def add_expense(
    date: str,
    amount: float,
    category: str,
    subcategory: str = "",
    note: str = "",
) -> dict[str, int | str]:
    """Add an expense with its date, amount, category, and optional details."""
    return save_expense(date, amount, category, subcategory, note)


@mcp.tool()
def get_expense(expense_id: int) -> dict[str, object] | None:
    """Get one expense by ID, or return None if it does not exist."""
    return fetch_expense(expense_id)


@mcp.tool()
def update_expense(
    expense_id: int,
    date: str | None = None,
    amount: float | None = None,
    category: str | None = None,
    subcategory: str | None = None,
    note: str | None = None,
) -> dict[str, object] | None:
    """Update provided fields on an expense and return it, or None if absent."""
    return revise_expense(expense_id, date, amount, category, subcategory, note)


@mcp.tool()
def delete_expense(expense_id: int) -> bool:
    """Delete an expense by ID and report whether it existed."""
    return remove_expense(expense_id)


@mcp.tool()
def list_expenses(start_date: str, end_date: str) -> list[dict[str, object]]:
    """List expenses within an inclusive start and end date range."""
    return fetch_expenses(start_date, end_date)


@mcp.tool()
def summarize(
    start_date: str,
    end_date: str,
    category: str | None = None,
) -> list[dict[str, object]]:
    """Summarize expense totals by category in an inclusive date range."""
    return summarize_expenses(start_date, end_date, category)


@mcp.resource("expense://categories", mime_type="application/json")
def categories() -> str:
    """Return the current expense category and subcategory definitions."""
    return CATEGORIES_PATH.read_text(encoding="utf-8")


def main() -> None:
    """Run the SmartSpend MCP server over HTTP on port 8000."""
    print("Starting SmartSpend MCP Server on http://127.0.0.1:8000/mcp ...")
    mcp.run(transport="http", port=8000)


if __name__ == "__main__":
    main()
