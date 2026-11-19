"""Tests for SmartSpend's LangChain agent setup."""

from datetime import date
import unittest
from unittest.mock import patch

from mcp_server import langchain_client


class ExpenseAgentTests(unittest.TestCase):
    @patch("mcp_server.langchain_client.create_agent")
    @patch("mcp_server.langchain_client.init_chat_model")
    def test_yearless_dates_use_the_current_year(
        self, init_chat_model, create_agent
    ) -> None:
        create_agent.return_value = object()

        langchain_client.create_expense_agent([], "test-model")

        prompt = create_agent.call_args.kwargs["system_prompt"]
        today = date.today()
        self.assertIn(f"The current date is {today.isoformat()}.", prompt)
        self.assertIn(
            f"without a year, use the current year ({today.year})",
            prompt,
        )
        self.assertIn("YYYY-MM-DD format", prompt)


if __name__ == "__main__":
    unittest.main()
