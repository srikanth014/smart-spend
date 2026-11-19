# SmartSpend MCP Server

SmartSpend is an expense-tracking [Model Context Protocol](https://modelcontextprotocol.io/) server built with FastMCP and SQLite. It provides tools for recording and editing expenses, browsing expenses by date, and summarizing spending by category. The Streamlit dashboard combines spending charts with the LangChain/Groq conversational assistant.

## Requirements

- Python 3.13 or newer
- [uv](https://docs.astral.sh/uv/) (recommended)
- A Groq API key only if you plan to use the conversational agent

## Install

```bash
uv sync
```

To use the chat assistant, copy `.env.example` to `.env` and set `GROQ_API_KEY`. `GROQ_MODEL` is optional.

## Run

Start the server:

```bash
uv run smartspend-server
# or: uv run python -m mcp_server.server
```

The HTTP MCP endpoint is `http://127.0.0.1:8000/mcp`. The server creates `data/expenses.db` automatically.

Run the MCP client demonstration in another terminal:

```bash
uv run smartspend-client
```

The demo adds a sample expense dated today, then lists and summarizes today's expenses.

Run the conversational agent:

```bash
uv run smartspend-agent
```

Run the Streamlit dashboard with charts and the conversational assistant:

```bash
uv run streamlit run src/mcp_server/dashboard.py
```

The dashboard uses the same SQLite database and in-process MCP tools, so it does not require the separate MCP HTTP server to be running. Its main page has the expense chat, current-month spending metrics and category totals, plus a six-month spending trend. Add expenses or ask questions in chat; set `GROQ_API_KEY` in `.env` to enable it. The `smartspend-agent` CLI remains available.

## MCP tools and resource

| Name | Parameters | Behavior |
| --- | --- | --- |
| `add_expense` | `date: str`, `amount: float`, `category: str`, `subcategory: str = ""`, `note: str = ""` | Records an expense and returns its generated ID. |
| `get_expense` | `expense_id: int` | Returns one expense by ID, or `None` if it does not exist. |
| `update_expense` | `expense_id: int`, optional `date`, `amount`, `category`, `subcategory`, `note` | Updates the supplied fields and returns the expense, or `None` if it does not exist. At least one field must be supplied. |
| `delete_expense` | `expense_id: int` | Deletes an expense and returns whether a record was deleted. |
| `list_expenses` | `start_date: str`, `end_date: str` | Lists records between the dates, inclusive. |
| `summarize` | `start_date: str`, `end_date: str`, `category: str \| None = None` | Returns expense totals grouped by category; optionally filters to one category. |
| `expense://categories` | — | JSON category and subcategory list from `src/mcp_server/categories.json`, read fresh for each request. |

Expense writes validate that amounts are greater than zero, dates are real ISO dates (`YYYY-MM-DD`), and categories exist in `categories.json`. Date-range tools also validate ISO dates and require the start date to be on or before the end date.

## MCP host configuration

The repository's `.mcp.json` configures the server at `http://127.0.0.1:8000/mcp`. Other MCP hosts can use the same HTTP endpoint.

## Storage

Expenses are stored in the `expenses` table in `data/expenses.db`.
