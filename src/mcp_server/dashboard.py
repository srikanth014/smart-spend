"""Streamlit dashboard for SmartSpend expenses and the LangChain assistant."""

import asyncio
from datetime import date, timedelta
import os
from pathlib import Path
from typing import Any

import plotly.express as px
import streamlit as st
from dotenv import dotenv_values, load_dotenv
from fastmcp import Client
from langchain.messages import AIMessage, HumanMessage
from langchain.mcp import MCPAdapter

from mcp_server import database
from mcp_server.langchain_client import DEFAULT_GROQ_MODEL, create_expense_agent
from mcp_server.server import mcp

DOTENV_PATH = Path(__file__).resolve().parents[2] / ".env"
CHAT_PANEL_HEIGHT = 320
EMPTY_CHAT_PANEL_HEIGHT = 130
load_dotenv(DOTENV_PATH)


def _configured_groq_model() -> str:
    """Read the current .env model to avoid stale Streamlit process settings."""
    file_model = dotenv_values(DOTENV_PATH).get("GROQ_MODEL")
    return (file_model or os.getenv("GROQ_MODEL") or DEFAULT_GROQ_MODEL).strip()


def _shift_month(month: date, offset: int) -> date:
    month_index = month.year * 12 + month.month - 1 + offset
    year, zero_based_month = divmod(month_index, 12)
    return date(year, zero_based_month + 1, 1)


def _monthly_totals(
    expenses: list[dict[str, Any]],
    first_month: date,
    month_count: int,
) -> list[dict[str, Any]]:
    months = [_shift_month(first_month, offset) for offset in range(month_count)]
    totals = {month.strftime("%Y-%m"): 0.0 for month in months}
    for expense in expenses:
        month_key = str(expense["date"])[:7]
        if month_key in totals:
            totals[month_key] += float(expense["amount"])
    return [
        {"month": month, "amount": totals[month.strftime("%Y-%m")]}
        for month in months
    ]


def _chat_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = [
            part["text"]
            for part in content
            if isinstance(part, dict) and isinstance(part.get("text"), str)
        ]
        if text_parts:
            return "\n".join(text_parts)
    return str(content)


async def _ask_agent(
    history: list[dict[str, str]],
    model_name: str,
) -> str:
    messages = [
        HumanMessage(content=message["content"])
        if message["role"] == "user"
        else AIMessage(content=message["content"])
        for message in history
    ]
    async with MCPAdapter(Client(mcp)) as adapter:
        tools = await adapter.list_tools()
        agent = create_expense_agent(tools, model_name)
        result = await agent.ainvoke({"messages": messages})
    return _chat_text(result["messages"][-1].content)


def main() -> None:
    """Render the expense analytics and chat interface."""
    st.set_page_config(page_title="SmartSpend", page_icon="💸", layout="wide")
    st.markdown(
        """
        <style>
        [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(ellipse at 8% 0%, rgba(196, 236, 220, 0.55), transparent 34%),
                radial-gradient(ellipse at 96% 8%, rgba(218, 231, 255, 0.55), transparent 30%),
                #f6f8fb;
        }
        [data-testid="stHeader"] { background: transparent; }
        .main .block-container {
            max-width: 1180px;
            padding-top: 2rem;
            padding-bottom: 4rem;
        }
        .smartspend-hero {
            display: flex;
            align-items: center;
            gap: 1.1rem;
            margin: 0.3rem 0 1.8rem;
            padding: 1.4rem 1.6rem;
            border: 1px solid rgba(255, 255, 255, 0.8);
            border-radius: 24px;
            background: linear-gradient(115deg, rgba(255,255,255,.92), rgba(247,251,255,.83));
            box-shadow: 0 14px 40px rgba(34, 54, 82, 0.07);
        }
        .smartspend-mark {
            display: grid;
            place-items: center;
            flex: 0 0 54px;
            width: 54px;
            height: 54px;
            border-radius: 18px;
            color: white;
            background: linear-gradient(145deg, #087e72, #16a085);
            font-size: 1.7rem;
            font-weight: 750;
            box-shadow: 0 8px 18px rgba(16, 145, 122, 0.2);
        }
        .smartspend-eyebrow {
            color: #0c8978;
            font-size: .72rem;
            font-weight: 750;
            letter-spacing: .13em;
        }
        .smartspend-title {
            margin: .15rem 0;
            color: #142a3b;
            font-size: clamp(1.65rem, 3vw, 2.25rem);
            font-weight: 760;
            letter-spacing: -.045em;
            line-height: 1.15;
        }
        .smartspend-copy { color: #657587; font-size: .96rem; }
        h2, h3, h4 { color: #1b3042; letter-spacing: -.025em; }
        [data-testid="stMetric"] {
            min-height: 112px;
            padding: 1.05rem 1.2rem;
            border: 1px solid #e6ecf2;
            border-radius: 18px;
            background: rgba(255,255,255,.9);
            box-shadow: 0 8px 24px rgba(34, 54, 82, .045);
        }
        [data-testid="stMetricLabel"] {
            color: #657587;
            font-weight: 600;
        }
        [data-testid="stMetricValue"] {
            color: #18384a;
            font-weight: 730;
            letter-spacing: -.035em;
        }
        [data-testid="stVerticalBlockBorderWrapper"] {
            border-color: #e6ecf2;
            border-radius: 20px;
            background: rgba(255,255,255,.72);
            box-shadow: 0 8px 24px rgba(34, 54, 82, .035);
        }
        [data-testid="stChatMessage"] {
            border: 1px solid #e8edf2;
            border-radius: 16px;
            background: #fff;
        }
        [data-testid="stChatInput"] > div {
            border-color: #dce5eb;
            border-radius: 16px;
            background: #fff;
            box-shadow: 0 5px 16px rgba(34, 54, 82, .06);
        }
        [data-testid="stChatInput"] textarea { font-size: .98rem; }
        [data-testid="stBaseButton-primary"] {
            border: 0;
            border-radius: 12px;
            background: linear-gradient(120deg, #087e72, #14977f);
        }
        @media (max-width: 640px) {
            .main .block-container { padding: 1rem 1rem 2rem; }
            .smartspend-hero { gap: .85rem; padding: 1.1rem; border-radius: 20px; }
            .smartspend-mark { flex-basis: 46px; width: 46px; height: 46px; border-radius: 15px; }
        }
        </style>
        <div class="smartspend-hero">
            <div class="smartspend-mark">₹</div>
            <div>
                <div class="smartspend-eyebrow">SMARTSPEND · PERSONAL FINANCE</div>
                <div class="smartspend-title">Your money, in focus.</div>
                <div class="smartspend-copy">A clearer view of your spending, with a little help from AI.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    today = date.today()
    selected_month = today.replace(day=1)
    month_end = _shift_month(selected_month, 1) - timedelta(days=1)
    trend_month_count = 6
    month_expenses = database.list_expenses(
        selected_month.isoformat(),
        month_end.isoformat(),
    )
    trend_start = _shift_month(selected_month, -(trend_month_count - 1))
    trend_expenses = database.list_expenses(
        trend_start.isoformat(),
        month_end.isoformat(),
    )
    category_totals = database.summarize(
        selected_month.isoformat(),
        month_end.isoformat(),
    )

    total_spent = sum(float(expense["amount"]) for expense in month_expenses)
    expense_count = len(month_expenses)
    average_expense = total_spent / expense_count if expense_count else 0.0
    metric_columns = st.columns(3)
    with metric_columns[0]:
        st.metric("Spent this month", f"₹{total_spent:,.2f}")
    with metric_columns[1]:
        st.metric("Expenses", f"{expense_count}")
    with metric_columns[2]:
        st.metric("Average expense", f"₹{average_expense:,.2f}")

    st.subheader(f"Analytics · {selected_month.strftime('%B %Y')}")
    category_column, trend_column = st.columns(2)
    with category_column:
        with st.container(border=True):
            st.markdown("#### Spending by category")
            if category_totals:
                category_chart = px.bar(
                    category_totals,
                    x="total_amount",
                    y="category",
                    orientation="h",
                    labels={"total_amount": "Amount (₹)", "category": "Category"},
                    text_auto=".2f",
                    color_discrete_sequence=["#109681"],
                    template="plotly_white",
                )
                category_chart.update_layout(
                    yaxis={"categoryorder": "total ascending"},
                    margin={"l": 8, "r": 8, "t": 12, "b": 8},
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font={"family": "Inter, sans-serif", "color": "#526477"},
                )
                st.plotly_chart(category_chart, width="stretch")
            else:
                st.info("No expenses recorded for this month.")

    with trend_column:
        with st.container(border=True):
            st.markdown("#### Monthly trend")
            trend_rows = _monthly_totals(
                trend_expenses,
                trend_start,
                trend_month_count,
            )
            trend_chart = px.area(
                trend_rows,
                x="month",
                y="amount",
                markers=True,
                labels={"month": "Month", "amount": "Amount (₹)"},
                color_discrete_sequence=["#3289bd"],
                template="plotly_white",
            )
            trend_chart.update_traces(
                line={"color": "#3289bd", "width": 3},
                fillcolor="rgba(50,137,189,.12)",
                marker={"size": 8, "color": "#3289bd"},
            )
            trend_chart.update_layout(
                margin={"l": 8, "r": 8, "t": 12, "b": 8},
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font={"family": "Inter, sans-serif", "color": "#526477"},
                hovermode="x unified",
            )
            st.plotly_chart(trend_chart, width="stretch")

    api_key = os.getenv("GROQ_API_KEY", "").strip()
    model_name = _configured_groq_model()
    st.subheader("Expense assistant")
    if not api_key:
        st.warning("Set GROQ_API_KEY in your .env file to enable chat.")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    chat_panel_height = (
        CHAT_PANEL_HEIGHT
        if st.session_state.chat_history
        else EMPTY_CHAT_PANEL_HEIGHT
    )
    with st.container(height=chat_panel_height, border=True):
        if not st.session_state.chat_history:
            st.caption("Ask about your spending or tell me about an expense to add.")
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        prompt = st.chat_input(
            "Ask about spending or add an expense",
            disabled=not api_key,
        )
    if prompt:
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.spinner("SmartSpend is thinking..."):
            try:
                answer = asyncio.run(
                    _ask_agent(st.session_state.chat_history, model_name)
                )
            except Exception as exc:
                st.error(f"Unable to get a response from the expense assistant: {exc}")
            else:
                st.session_state.chat_history.append(
                    {"role": "assistant", "content": answer}
                )
                st.rerun()


if __name__ == "__main__":
    main()
