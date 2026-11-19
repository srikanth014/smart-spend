"""SQLite persistence for SmartSpend expense records."""

from pathlib import Path
import sqlite3
from typing import Any

project_root = Path(__file__).resolve().parents[2]
data_dir = project_root / "data"
db_path = data_dir / "expenses.db"


def get_connection() -> sqlite3.Connection:
    """Create a connection to the expense database."""
    data_dir.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    """Create the expenses table when it does not already exist."""
    connection = get_connection()
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT NOT NULL DEFAULT '',
                note TEXT NOT NULL DEFAULT ''
            )
            """
        )
        connection.commit()
    finally:
        connection.close()


def add_expense(
    date: str,
    amount: float,
    category: str,
    subcategory: str = "",
    note: str = "",
) -> dict[str, Any]:
    """Insert an expense and return its generated database ID."""
    connection = get_connection()
    try:
        cursor = connection.execute(
            """
            INSERT INTO expenses (date, amount, category, subcategory, note)
            VALUES (?, ?, ?, ?, ?)
            """,
            (date, amount, category, subcategory, note),
        )
        connection.commit()
        return {"status": "ok", "id": cursor.lastrowid}
    finally:
        connection.close()


def list_expenses(start_date: str, end_date: str) -> list[dict[str, Any]]:
    """Return expenses in an inclusive date range, ordered by insertion ID."""
    connection = get_connection()
    try:
        rows = connection.execute(
            """
            SELECT id, date, amount, category, subcategory, note
            FROM expenses
            WHERE date BETWEEN ? AND ?
            ORDER BY id ASC
            """,
            (start_date, end_date),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def summarize(
    start_date: str,
    end_date: str,
    category: str | None = None,
) -> list[dict[str, Any]]:
    """Sum expenses by category over an inclusive date range."""
    connection = get_connection()
    try:
        query = """
            SELECT category, SUM(amount) AS total_amount
            FROM expenses
            WHERE date BETWEEN ? AND ?
        """
        parameters: list[str] = [start_date, end_date]
        if category:
            query += " AND category = ?"
            parameters.append(category)
        query += " GROUP BY category ORDER BY category ASC"

        rows = connection.execute(query, parameters).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


init_db()
