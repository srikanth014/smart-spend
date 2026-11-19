"""LangChain AI Agent with SmartSpend FastMCP integration and Groq LLM.

Connects to the SmartSpend MCP server via LangChain's MCPAdapter, loads its
tools dynamically, and enables natural language expense tracking.
"""

import asyncio
import json
import os
import sys
from datetime import date
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.tools import BaseTool
from langchain.mcp import MCPAdapter
from langchain.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.state import CompiledStateGraph

# Load environment variables from .env file
load_dotenv()

MCP_SERVER_URL = "http://127.0.0.1:8000/mcp"
CATEGORIES_PATH = Path(__file__).with_name("categories.json")
DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"


def check_environment() -> tuple[str, str]:
    """Validate required environment variables for the Groq model provider.

    Returns:
        tuple[str, str]: The GROQ_API_KEY and GROQ_MODEL values.

    Raises:
        SystemExit: If GROQ_API_KEY is not configured.
    """
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    model = os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL).strip()

    if not api_key:
        print("\n[Configuration Error] GROQ_API_KEY is not set.")
        print("Please configure your .env file:")
        print("  1. Copy .env.example to .env:  cp .env.example .env")
        print("  2. Add your Groq API key:      GROQ_API_KEY=gsk_...")
        print(f"  3. (Optional) Set your model:   GROQ_MODEL={DEFAULT_GROQ_MODEL}\n")
        sys.exit(1)

    return api_key, model


def create_expense_agent(
    tools: list[BaseTool],
    model_name: str,
    checkpointer: InMemorySaver | None = None,
) -> CompiledStateGraph:
    """Create the SmartSpend LangChain agent for the given MCP tools."""
    category_definitions = json.loads(CATEGORIES_PATH.read_text(encoding="utf-8"))
    model = init_chat_model(model_name, model_provider="groq")
    today = date.today()
    return create_agent(
        model=model,
        tools=tools,
        system_prompt=(
            "You are SmartSpend, a helpful personal expense tracking assistant. "
            "You can add, update, delete, get, list, and summarize expenses using "
            "your available tools. When recording an expense, select a category "
            "and subcategory from this list: "
            f"{json.dumps(category_definitions)}. The current date is "
            f"{today.isoformat()}. Resolve relative dates using this date. "
            f"When a user gives a calendar date without a year, use the current "
            f"year ({today.year}) and pass the tool date in YYYY-MM-DD format. "
            "Always confirm recorded or "
            "changed amounts, dates, and categories clearly."
        ),
        checkpointer=checkpointer,
    )


async def run_agent() -> None:
    """Initialize and run the interactive LangChain agent session."""
    _, model_name = check_environment()

    print("=" * 60)
    print("Initializing SmartSpend AI Agent (Groq + FastMCP)")
    print(f"Connecting to MCP server at: {MCP_SERVER_URL}")
    print(f"Using Groq model: {model_name}")
    print("=" * 60)

    adapter = MCPAdapter(MCP_SERVER_URL)

    try:
        async with adapter:
            # Dynamically fetch all tools exposed by the MCP server
            tools = await adapter.list_tools()
            print(f"Loaded {len(tools)} tools from MCP server:")
            for tool in tools:
                print(f" - {getattr(tool, 'name', tool)}")

            agent = create_expense_agent(
                tools,
                model_name,
                checkpointer=InMemorySaver(),
            )

            # Conversation thread configuration
            thread_id = str(uuid4())
            config = {"configurable": {"thread_id": thread_id}}

            print("\nAgent initialized! Ask about your expenses or enter 'q' / 'exit' to quit.\n")

            # Initial greeting
            initial_prompt = "Hello! How can you help me understand and track my spending?"
            print(f"User: {initial_prompt}\n")
            print("AI thinking...")
            result = await agent.ainvoke(
                {"messages": [HumanMessage(content=initial_prompt)]},
                config=config,
            )
            last_message = result["messages"][-1]
            ai_text = getattr(last_message, "content", getattr(last_message, "text", str(last_message)))
            print(f"AI: {ai_text}\n")

            # Interactive chat loop
            while True:
                try:
                    user_input = input("You (q to exit): ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\nExiting session. Goodbye!")
                    break

                if not user_input:
                    continue

                if user_input.lower() in ("q", "quit", "exit"):
                    print("Goodbye!")
                    break

                print("\nAI thinking...")
                result = await agent.ainvoke(
                    {"messages": [HumanMessage(content=user_input)]},
                    config=config,
                )
                last_message = result["messages"][-1]
                ai_text = getattr(last_message, "content", getattr(last_message, "text", str(last_message)))
                print(f"\nAI: {ai_text}\n")

    except ConnectionRefusedError:
        print(f"\n[Error] Connection refused to MCP server at {MCP_SERVER_URL}.")
        print("Please start the MCP server before running this agent:")
        print("  uv run smartspend-server")
        print("  # or: uv run python -m mcp_server.server\n")
    except Exception as exc:
        print(f"\n[Error] An unexpected error occurred: {exc}")
        print("Please check that your MCP server is running and your GROQ_API_KEY is valid.\n")


def main() -> None:
    """Synchronous entry point for the LangChain agent."""
    try:
        asyncio.run(run_agent())
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting.")


if __name__ == "__main__":
    main()
