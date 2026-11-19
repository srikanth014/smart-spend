"""Tests for SmartSpend's SQLite persistence layer."""

import tempfile
import unittest
from pathlib import Path

from mcp_server import database
from pydantic import ValidationError


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

    def test_add_rejects_invalid_expense_data(self) -> None:
        invalid_expenses = [
            ("2026-11-01", 0, "food"),
            ("2026-11-01", -1, "food"),
            ("2026-11-01", float("inf"), "food"),
            ("2026-11-01", float("nan"), "food"),
            ("2026-02-30", 10, "food"),
            ("20261101", 10, "food"),
            ("2026-11-01", 10, "unknown"),
        ]
        for date, amount, category in invalid_expenses:
            with self.subTest(date=date, amount=amount, category=category):
                with self.assertRaises(ValidationError):
                    database.add_expense(date, amount, category)

        self.assertEqual(database.list_expenses("2026-11-01", "2026-11-30"), [])

    def test_get_update_and_delete_expense(self) -> None:
        added = database.add_expense("2026-11-01", 24.5, "food", "groceries", "Shop")
        expense_id = added["id"]

        self.assertEqual(database.get_expense(expense_id)["note"], "Shop")
        updated = database.update_expense(
            expense_id,
            amount=30,
            note="Updated amount",
        )
        self.assertEqual(updated["amount"], 30)
        self.assertEqual(updated["date"], "2026-11-01")
        self.assertEqual(updated["note"], "Updated amount")
        self.assertIsNone(database.get_expense(999))
        self.assertIsNone(database.update_expense(999, note="missing"))

        with self.assertRaises(ValidationError):
            database.update_expense(expense_id, amount=0)
        with self.assertRaises(ValidationError):
            database.update_expense(expense_id, date="2026-02-30")
        with self.assertRaises(ValidationError):
            database.update_expense(expense_id, category="unknown")
        with self.assertRaises(ValidationError):
            database.update_expense(expense_id)
        self.assertEqual(database.get_expense(expense_id), updated)

        self.assertTrue(database.delete_expense(expense_id))
        self.assertFalse(database.delete_expense(expense_id))
        self.assertIsNone(database.get_expense(expense_id))

    def test_date_ranges_and_summary_category_are_validated(self) -> None:
        with self.assertRaises(ValidationError):
            database.list_expenses("2026-11-02", "2026-11-01")
        with self.assertRaises(ValidationError):
            database.summarize("2026-11-01", "2026-11-02", "unknown")


if __name__ == "__main__":
    unittest.main()
