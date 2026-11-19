"""Tests for SmartSpend dashboard analytics."""

from datetime import date
import os
import unittest
from unittest.mock import patch

from mcp_server.dashboard import (
    CHAT_PANEL_HEIGHT,
    EMPTY_CHAT_PANEL_HEIGHT,
    _configured_groq_model,
    _daily_totals,
    _shift_month,
)
from mcp_server.langchain_client import DEFAULT_GROQ_MODEL, check_environment


class DashboardAnalyticsTests(unittest.TestCase):
    @patch(
        "mcp_server.dashboard.dotenv_values",
        return_value={"GROQ_MODEL": "openai/gpt-oss-20b"},
    )
    def test_dashboard_uses_current_env_file_model(self, _dotenv_values) -> None:
        with patch.dict(os.environ, {"GROQ_MODEL": "llama-3.3-70b-versatile"}):
            self.assertEqual(_configured_groq_model(), "openai/gpt-oss-20b")

    def test_default_groq_model_is_used_when_no_override_is_configured(self) -> None:
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}, clear=True):
            self.assertEqual(check_environment(), ("test-key", DEFAULT_GROQ_MODEL))
        self.assertEqual(DEFAULT_GROQ_MODEL, "openai/gpt-oss-120b")

    def test_chat_panel_has_compact_minimum_and_fixed_maximum(self) -> None:
        self.assertEqual(EMPTY_CHAT_PANEL_HEIGHT, 130)
        self.assertEqual(CHAT_PANEL_HEIGHT, 400)

    def test_shift_month_handles_year_boundaries(self) -> None:
        self.assertEqual(_shift_month(date(2026, 1, 1), -1), date(2025, 12, 1))
        self.assertEqual(_shift_month(date(2025, 12, 1), 2), date(2026, 2, 1))

    def test_daily_totals_include_zero_spend_days(self) -> None:
        expenses = [
            {"date": "2026-01-03", "amount": 12.5},
            {"date": "2026-01-03", "amount": 7.5},
            {"date": "2026-01-05", "amount": 20.0},
            {"date": "2026-01-06", "amount": 50.0},
        ]

        self.assertEqual(
            _daily_totals(expenses, date(2026, 1, 3), date(2026, 1, 5)),
            [
                {"day": date(2026, 1, 3), "amount": 20.0},
                {"day": date(2026, 1, 4), "amount": 0.0},
                {"day": date(2026, 1, 5), "amount": 20.0},
            ],
        )


if __name__ == "__main__":
    unittest.main()
