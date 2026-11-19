"""SQLite persistence for SmartSpend expense records."""

import json
import sqlite3
from datetime import date as calendar_date
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, TypeAdapter, field_validator, model_validator

project_root = Path(__file__).resolve().parents[2]
data_dir = project_root / "data"
db_path = data_dir / "expenses.db"
CATEGORIES_PATH = Path(__file__).with_name("categories.json")


def _validate_iso_date(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("must be an ISO date in YYYY-MM-DD format")
    try:
        parsed_date = calendar_date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("must be a real ISO date in YYYY-MM-DD format") from exc
    if parsed_date.isoformat() != value:
        raise ValueError("must be an ISO date in YYYY-MM-DD format")
    return value


def _category_names() -> set[str]:
    categories = TypeAdapter(dict[str, list[str]]).validate_python(
        json.loads(CATEGORIES_PATH.read_text(encoding="utf-8"))
    )
    return set(categories)


def _validate_category(value: str) -> str:
    if value not in _category_names():
        raise ValueError(f"unsupported category: {value}")
    return value


class ExpenseInput(BaseModel):
    date: str
    amount: float = Field(gt=0, allow_inf_nan=False)
    category: str
    subcategory: str = ""
    note: str = ""

    @field_validator("date")
    @classmethod
    def validate_date(cls, value: str) -> str:
        return _validate_iso_date(value)

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        return _validate_category(value)


class ExpenseUpdate(BaseModel):
    date: str | None = None
    amount: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    category: str | None = None
    subcategory: str | None = None
    note: str | None = None

    @field_validator("date")
    @classmethod
    def validate_date(cls, value: str | None) -> str | None:
        return _validate_iso_date(value) if value is not None else None

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str | None) -> str | None:
        return _validate_category(value) if value is not None else None

    @model_validator(mode="after")
    def require_changes(self) -> "ExpenseUpdate":
        if not self.model_fields_set:
            raise ValueError("at least one expense field must be provided")
        return self


class CategoryFilter(BaseModel):
    category: str

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        return _validate_category(value)


class DateRange(BaseModel):
    start_date: str
    end_date: str

    @field_validator("start_date", "end_date")
    @classmethod
    def validate_date(cls, value: str) -> str:
        return _validate_iso_date(value)

    @model_validator(mode="after")
    def validate_order(self) -> "DateRange":
        if self.start_date > self.end_date:
            raise ValueError("start_date must be on or before end_date")
        return self


class ExpenseIdentifier(BaseModel):
    value: int = Field(gt=0)


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
    expense = ExpenseInput(
        date=date,
        amount=amount,
        category=category,
        subcategory=subcategory,
        note=note,
    )
    connection = get_connection()
    try:
        cursor = connection.execute(
            """
            INSERT INTO expenses (date, amount, category, subcategory, note)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                expense.date,
                expense.amount,
                expense.category,
                expense.subcategory,
                expense.note,
            ),
        )
        connection.commit()
        return {"status": "ok", "id": cursor.lastrowid}
    finally:
        connection.close()


def list_expenses(start_date: str, end_date: str) -> list[dict[str, Any]]:
    """Return expenses in an inclusive date range, ordered by insertion ID."""
    date_range = DateRange(start_date=start_date, end_date=end_date)
    connection = get_connection()
    try:
        rows = connection.execute(
            """
            SELECT id, date, amount, category, subcategory, note
            FROM expenses
            WHERE date BETWEEN ? AND ?
            ORDER BY id ASC
            """,
            (date_range.start_date, date_range.end_date),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def get_expense(expense_id: int) -> dict[str, Any] | None:
    """Return one expense by ID, or None when it does not exist."""
    identifier = ExpenseIdentifier(value=expense_id).value
    connection = get_connection()
    try:
        row = connection.execute(
            """
            SELECT id, date, amount, category, subcategory, note
            FROM expenses
            WHERE id = ?
            """,
            (identifier,),
        ).fetchone()
        return dict(row) if row is not None else None
    finally:
        connection.close()


def update_expense(
    expense_id: int,
    date: str | None = None,
    amount: float | None = None,
    category: str | None = None,
    subcategory: str | None = None,
    note: str | None = None,
) -> dict[str, Any] | None:
    """Update provided expense fields and return the record, or None if absent."""
    identifier = ExpenseIdentifier(value=expense_id).value
    changes = {
        key: value
        for key, value in {
            "date": date,
            "amount": amount,
            "category": category,
            "subcategory": subcategory,
            "note": note,
        }.items()
        if value is not None
    }
    expense = ExpenseUpdate(**changes)
    updates = expense.model_dump(exclude_unset=True)
    assignments = ", ".join(f"{field} = ?" for field in updates)

    connection = get_connection()
    try:
        cursor = connection.execute(
            f"UPDATE expenses SET {assignments} WHERE id = ?",
            (*updates.values(), identifier),
        )
        if cursor.rowcount == 0:
            return None

        row = connection.execute(
            """
            SELECT id, date, amount, category, subcategory, note
            FROM expenses
            WHERE id = ?
            """,
            (identifier,),
        ).fetchone()
        connection.commit()
        return dict(row) if row is not None else None
    finally:
        connection.close()


def delete_expense(expense_id: int) -> bool:
    """Delete an expense by ID and report whether a record was deleted."""
    identifier = ExpenseIdentifier(value=expense_id).value
    connection = get_connection()
    try:
        cursor = connection.execute("DELETE FROM expenses WHERE id = ?", (identifier,))
        connection.commit()
        return cursor.rowcount > 0
    finally:
        connection.close()


def summarize(
    start_date: str,
    end_date: str,
    category: str | None = None,
) -> list[dict[str, Any]]:
    """Sum expenses by category over an inclusive date range."""
    date_range = DateRange(start_date=start_date, end_date=end_date)
    if category is not None:
        category = CategoryFilter(category=category).category

    connection = get_connection()
    try:
        query = """
            SELECT category, SUM(amount) AS total_amount
            FROM expenses
            WHERE date BETWEEN ? AND ?
        """
        parameters: list[str] = [date_range.start_date, date_range.end_date]
        if category:
            query += " AND category = ?"
            parameters.append(category)
        query += " GROUP BY category ORDER BY category ASC"

        rows = connection.execute(query, parameters).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


init_db()
