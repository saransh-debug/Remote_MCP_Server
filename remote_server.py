import sqlite3
import os
import time

from fastmcp import FastMCP

mcp = FastMCP(name="Expense Tracker")


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_DIR, "expense.db")

FILE_PATH = os.path.join(
    BASE_DIR,
    "expenses_json.json"
)


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_db():
    """
    Create a new SQLite connection for each request.

    WAL allows multiple readers while a writer is active.
    busy_timeout makes SQLite wait for a lock instead of
    immediately throwing 'database is locked'.
    """

    conn = sqlite3.connect(
        DB_PATH,
        timeout=30,
        check_same_thread=False
    )

    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA foreign_keys=ON")

    return conn


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_db():

    with get_db() as conn:

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
# TOOL: ADD EXPENSE
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

    max_retries = 5

    for attempt in range(max_retries):

        try:

            with get_db() as conn:

                cursor = conn.execute(
                    """
                    INSERT INTO expenses
                    (
                        date,
                        amount,
                        category,
                        subcategory,
                        note
                    )
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

        except sqlite3.OperationalError as e:

            if "locked" not in str(e).lower():
                raise

            if attempt == max_retries - 1:
                raise

            time.sleep(0.1 * (attempt + 1))


# ============================================================
# TOOL: LIST EXPENSES
# ============================================================

@mcp.tool
def list_expenses(
    start_date: str,
    end_date: str
):
    """
    Get expenses between two dates.
    """

    with get_db() as conn:

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
            ORDER BY date ASC, id ASC
            """,
            (
                start_date,
                end_date
            )
        )

        columns = [
            column[0]
            for column in cursor.description
        ]

        rows = cursor.fetchall()

        return [
            dict(zip(columns, row))
            for row in rows
        ]


# ============================================================
# TOOL: SUMMARISE
# ============================================================

@mcp.tool
def summarise(
    start_date: str,
    end_date: str,
    category: str = None
):
    """
    Summarise expenses between two dates.

    If category is provided, only that category
    is included.
    """

    with get_db() as conn:

        if category:

            cursor = conn.execute(
                """
                SELECT SUM(amount)
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
                SELECT SUM(amount)
                FROM expenses
                WHERE date BETWEEN ? AND ?
                """,
                (
                    start_date,
                    end_date
                )
            )

        total = cursor.fetchone()[0]

        return total or 0


# ============================================================
# RESOURCE: CATEGORIES
# ============================================================

@mcp.resource(
    "expense://categories",
    mime_type="application/json"
)
def categories():

    with open(
        FILE_PATH,
        "r",
        encoding="utf-8"
    ) as f:

        return f.read()


# ============================================================
# RESOURCE: SERVER INFO
# ============================================================

@mcp.resource("info://server")
def about_server():

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