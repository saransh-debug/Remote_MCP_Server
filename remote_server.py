import sqlite3
import os
from fastmcp import FastMCP

mcp = FastMCP(name="Expense Tracker")


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Use /tmp for the SQLite database in the deployed environment.
# NOTE: /tmp is writable, but its data may not survive redeployments.
DB_PATH = os.path.join("/tmp", "expense.db")

# This file is read-only application data, so it can stay
# alongside your source code.
FILE_PATH = os.path.join(BASE_DIR, "expenses_json.json")


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT DEFAULT '',
                note TEXT DEFAULT ''
            )
        """)

        conn.commit()


init_db()


# ============================================================
# TOOLS
# ============================================================

@mcp.tool
def add_expense(
    date: str,
    amount: float,
    category: str,
    subcategory: str = "",
    note: str = ""
):
    """
    Add a new expense.
    """

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            INSERT INTO expenses
            (date, amount, category, subcategory, note)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                date,
                amount,
                category,
                subcategory,
                note
            )
        )

        expense_id = cursor.lastrowid

        conn.commit()

    return {
        "success": True,
        "expense_id": expense_id,
        "message": "Expense added successfully"
    }


@mcp.tool
def list_expenses(
    start_date: str,
    end_date: str
):
    """
    Gives the list of expenses between two dates.
    """

    with sqlite3.connect(DB_PATH) as conn:

        cursor = conn.execute(
            """
            SELECT
                id,
                date,
                amount,
                category,
                subcategory,
                note
            FROM expenses
            WHERE date BETWEEN ? AND ?
            ORDER BY id ASC
            """,
            (
                start_date,
                end_date
            )
        )

        columns = [
            description[0]
            for description in cursor.description
        ]

        return [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]


@mcp.tool
def summarise(
    start_date: str,
    end_date: str,
    category: str = None
):
    """
    Summarises expenses between two dates.
    If category is provided, only that category is summarised.
    """

    with sqlite3.connect(DB_PATH) as conn:

        if category:

            cursor = conn.execute(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM expenses
                WHERE date BETWEEN ? AND ?
                AND category = ?
                """,
                (
                    start_date,
                    end_date,
                    category
                )
            )

        else:

            cursor = conn.execute(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM expenses
                WHERE date BETWEEN ? AND ?
                """,
                (
                    start_date,
                    end_date
                )
            )

        total = cursor.fetchone()[0]

    return {
        "start_date": start_date,
        "end_date": end_date,
        "category": category,
        "total": total
    }


# ============================================================
# RESOURCES
# ============================================================

@mcp.resource(
    "expense://categories",
    mime_type="application/json"
)
def categories():
    """
    Provides the available expense categories.
    """

    with open(
        FILE_PATH,
        "r",
        encoding="utf-8"
    ) as f:
        return f.read()


@mcp.resource("info://server")
def about_server():
    """
    Get information about the server.
    """

    return {
        "name": "Expense Tracker",
        "version": "1.0.0",
        "description": (
            "An MCP server that helps you "
            "track your expenses smartly."
        ),
        "transport": "HTTP",
        "host": "0.0.0.0",
        "port": 8000,
        "tools": [
            "add_expense",
            "list_expenses",
            "summarise"
        ],
        "resources": [
            "info://server",
            "expense://categories"
        ]
    }


# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=8000
    )