"""Tests for SmartSpend's SQLite persistence layer."""

import tempfile
import unittest
from pathlib import Path

from mcp_server import database


class ExpenseDatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_data_dir = database.data_dir
        self.original_db_path = database.db_path
        database.data_dir = Path(self.temp_dir.name)
        database.db_path = database.data_dir / "expenses.db"
        database.init_db()

    def tearDown(self) -> None:
        database.data_dir = self.original_data_dir
        database.db_path = self.original_db_path
        self.temp_dir.cleanup()

    def test_add_and_list_expenses_inclusive_date_range(self) -> None:
        added = database.add_expense(
            "2026-11-01", 24.5, "food", "groceries", "Weekly shop"
        )
        database.add_expense("2026-11-02", 8.0, "transport", "fuel")
        database.add_expense("2026-11-03", 15.0, "food", "dining_out")

        self.assertEqual(added, {"status": "ok", "id": 1})
        expenses = database.list_expenses("2026-11-01", "2026-11-02")
        self.assertEqual([expense["id"] for expense in expenses], [1, 2])
        self.assertEqual(expenses[0]["note"], "Weekly shop")

    def test_summarize_groups_and_filters_by_category(self) -> None:
        database.add_expense("2026-11-01", 24.5, "food")
        database.add_expense("2026-11-02", 8.0, "transport")
        database.add_expense("2026-11-03", 15.0, "food")

        self.assertEqual(
            database.summarize("2026-11-01", "2026-11-03"),
            [
                {"category": "food", "total_amount": 39.5},
                {"category": "transport", "total_amount": 8.0},
            ],
        )
        self.assertEqual(
            database.summarize("2026-11-01", "2026-11-03", "food"),
            [{"category": "food", "total_amount": 39.5}],
        )


if __name__ == "__main__":
    unittest.main()
