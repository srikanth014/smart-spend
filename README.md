# SmartSpend MCP Server

SmartSpend is an expense-tracking [Model Context Protocol](https://modelcontextprotocol.io/) server built with FastMCP and SQLite. It provides tools for recording expenses, browsing expenses by date, and summarizing spending by category. The repository also includes a direct MCP client and an optional LangChain/Groq conversational agent.

## Requirements

- Python 3.13 or newer
- [uv](https://docs.astral.sh/uv/) (recommended)
- A Groq API key only if you plan to use the conversational agent

## Install

```bash
uv sync
```

To use the agent, copy `.env.example` to `.env` and set `GROQ_API_KEY`. `GROQ_MODEL` is optional.

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

## MCP tools and resource

| Name | Parameters | Behavior |
| --- | --- | --- |
| `add_expense` | `date: str`, `amount: float`, `category: str`, `subcategory: str = ""`, `note: str = ""` | Records an expense and returns its generated ID. |
| `list_expenses` | `start_date: str`, `end_date: str` | Lists records between the dates, inclusive. |
| `summarize` | `start_date: str`, `end_date: str`, `category: str \| None = None` | Returns expense totals grouped by category; optionally filters to one category. |
| `expense://categories` | — | JSON category and subcategory list from `src/mcp_server/categories.json`, read fresh for each request. |

Use ISO-formatted dates (`YYYY-MM-DD`) so lexicographic date-range filtering is chronological. `categories.json` includes the supported spending categories and subcategories.

## MCP host configuration

The repository's `.mcp.json` configures the server at `http://127.0.0.1:8000/mcp`. Other MCP hosts can use the same HTTP endpoint.

## Storage

Expenses are stored in the `expenses` table in `data/expenses.db`.
