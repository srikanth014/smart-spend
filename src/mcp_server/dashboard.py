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
CHAT_PANEL_HEIGHT = 400
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


def _daily_totals(
    expenses: list[dict[str, Any]],
    first_day: date,
    last_day: date,
) -> list[dict[str, Any]]:
    days = [
        first_day + timedelta(days=offset)
        for offset in range((last_day - first_day).days + 1)
    ]
    totals = {day: 0.0 for day in days}
    for expense in expenses:
        expense_day = date.fromisoformat(str(expense["date"]))
        if expense_day in totals:
            totals[expense_day] += float(expense["amount"])
    return [
        {"day": day, "amount": amount}
        for day, amount in totals.items()
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
                radial-gradient(ellipse at 8% 0%, rgba(31, 112, 103, 0.2), transparent 34%),
                radial-gradient(ellipse at 96% 8%, rgba(56, 87, 136, 0.18), transparent 30%),
                #0b1118;
        }
        [data-testid="stHeader"] { background: transparent; }
        [data-testid="stToolbar"] { right: 1rem; }
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
            border: 1px solid #263441;
            border-radius: 24px;
            background: linear-gradient(115deg, rgba(20, 32, 42, .97), rgba(17, 26, 38, .94));
            box-shadow: 0 16px 42px rgba(0, 0, 0, .22);
        }
        .smartspend-mark {
            display: grid;
            place-items: center;
            flex: 0 0 54px;
            width: 54px;
            height: 54px;
            border-radius: 18px;
            color: #06120f;
            background: linear-gradient(145deg, #55d6a5, #3aa98d);
            font-size: 1.7rem;
            font-weight: 750;
            box-shadow: 0 8px 22px rgba(53, 191, 147, .18);
        }
        .smartspend-eyebrow {
            color: #65d8ae;
            font-size: .72rem;
            font-weight: 750;
            letter-spacing: .13em;
        }
        .smartspend-title {
            margin: .15rem 0;
            color: #edf4f7;
            font-size: clamp(1.65rem, 3vw, 2.25rem);
            font-weight: 760;
            letter-spacing: -.045em;
            line-height: 1.15;
        }
        .smartspend-copy { color: #9aabb8; font-size: .96rem; }
        h1, h2, h3, h4 { color: #e6edf3; letter-spacing: -.025em; }
        [data-testid="stCaptionContainer"], [data-testid="stMarkdownContainer"] p {
            color: #a7b5c2;
        }
        [data-testid="stMetric"] {
            min-height: 112px;
            padding: 1.05rem 1.2rem;
            border: 1px solid #263542;
            border-radius: 18px;
            background: linear-gradient(145deg, #141f2a, #111a24);
            box-shadow: 0 10px 26px rgba(0, 0, 0, .16);
        }
        [data-testid="stMetricLabel"] {
            color: #9aaab7;
            font-weight: 600;
        }
        [data-testid="stMetricValue"] {
            color: #edf4f7;
            font-weight: 730;
            letter-spacing: -.035em;
        }
        [data-testid="stVerticalBlockBorderWrapper"] {
            border-color: #263542;
            border-radius: 20px;
            background: rgba(17, 26, 36, .86);
            box-shadow: 0 10px 28px rgba(0, 0, 0, .15);
        }
        [data-testid="stChatMessage"] {
            border: 1px solid #2a3946;
            border-radius: 16px;
            background: #16212b;
        }
        [data-testid="stChatInput"] > div {
            border-color: #344653;
            border-radius: 16px;
            background: #111a23;
            box-shadow: 0 6px 18px rgba(0, 0, 0, .18);
        }
        [data-testid="stChatInput"] { margin-bottom: .75rem; }
        [data-testid="stChatInput"] textarea { font-size: .98rem; }
        [data-testid="stBaseButton-primary"] {
            border: 0;
            border-radius: 12px;
            color: #06120f;
            background: linear-gradient(120deg, #55d6a5, #3aa98d);
        }
        [data-testid="stAlert"] {
            border: 1px solid #344653;
            border-radius: 14px;
            background: #141f2a;
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
    st.markdown(
        f"""
        <style>
        .st-key-expense-chat-panel {{
            min-height: {EMPTY_CHAT_PANEL_HEIGHT}px;
            max-height: {CHAT_PANEL_HEIGHT}px;
            overflow-y: auto;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    today = date.today()
    current_month = today.replace(day=1)
    month_options = [_shift_month(current_month, -offset) for offset in range(12)]
    heading_column, month_column = st.columns([3, 1])
    with month_column:
        selected_month = st.selectbox(
            "Analytics month",
            month_options,
            format_func=lambda month: month.strftime("%B %Y"),
            label_visibility="collapsed",
        )
    selected_month_end = min(
        _shift_month(selected_month, 1) - timedelta(days=1),
        today,
    )
    month_expenses = database.list_expenses(
        selected_month.isoformat(),
        selected_month_end.isoformat(),
    )
    trend_start = date(selected_month.year, 1, 1)
    year_end = date(selected_month.year, 12, 31)
    trend_end = min(year_end, today)
    trend_expenses = database.list_expenses(
        trend_start.isoformat(),
        trend_end.isoformat(),
    )
    category_totals = database.summarize(
        selected_month.isoformat(),
        selected_month_end.isoformat(),
    )

    total_spent = sum(float(expense["amount"]) for expense in month_expenses)
    expense_count = len(month_expenses)
    average_expense = total_spent / expense_count if expense_count else 0.0
    metric_columns = st.columns(3)
    with metric_columns[0]:
        st.metric(
            f"Spent in {selected_month.strftime('%B')}",
            f"₹{total_spent:,.2f}",
        )
    with metric_columns[1]:
        st.metric("Expenses", f"{expense_count}")
    with metric_columns[2]:
        st.metric("Average expense", f"₹{average_expense:,.2f}")

    with heading_column:
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
                    color_discrete_sequence=["#55d6a5"],
                    template="plotly_dark",
                )
                category_chart.update_layout(
                    yaxis={"categoryorder": "total ascending"},
                    margin={"l": 8, "r": 8, "t": 12, "b": 8},
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font={"family": "Inter, sans-serif", "color": "#b6c4ce"},
                    xaxis={"gridcolor": "#263542", "zerolinecolor": "#344653"},
                    yaxis_gridcolor="#263542",
                )
                st.plotly_chart(category_chart, width="stretch")
            else:
                st.info("No expenses recorded for this month.")

    with trend_column:
        with st.container(border=True):
            st.markdown(f"#### Daily trend · {selected_month.year}")
            trend_rows = _daily_totals(
                trend_expenses,
                trend_start,
                trend_end,
            )
            trend_chart = px.area(
                trend_rows,
                x="day",
                y="amount",
                labels={"day": "Day", "amount": "Amount (₹)"},
                color_discrete_sequence=["#3289bd"],
                template="plotly_dark",
            )
            trend_chart.update_traces(
                line={"color": "#78a9ff", "width": 3},
                fillcolor="rgba(120,169,255,.14)",
            )
            trend_chart.update_layout(
                margin={"l": 8, "r": 8, "t": 12, "b": 8},
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font={"family": "Inter, sans-serif", "color": "#b6c4ce"},
                hovermode="x unified",
                xaxis={
                    "gridcolor": "#263542",
                    "zerolinecolor": "#344653",
                    "tickformat": "%b",
                    "rangeslider": {
                        "visible": True,
                        "bgcolor": "#141f2a",
                        "bordercolor": "#344653",
                        "thickness": 0.12,
                    },
                },
                yaxis={"gridcolor": "#263542", "zerolinecolor": "#344653"},
            )
            st.plotly_chart(trend_chart, width="stretch")

    api_key = os.getenv("GROQ_API_KEY", "").strip()
    model_name = _configured_groq_model()
    st.subheader("Expense assistant")
    if not api_key:
        st.warning("Set GROQ_API_KEY in your .env file to enable chat.")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    with st.container(height="content", border=True, key="expense-chat-panel"):
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
