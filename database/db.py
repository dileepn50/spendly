import os
import sqlite3
from datetime import datetime

from werkzeug.security import generate_password_hash

# spendly.db lives in the project root, one directory above this file
# (database/db.py -> database/ -> project root). Computed via __file__ so it
# works regardless of the process's current working directory.
DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "spendly.db",
)


def get_db():
    """Open a new SQLite connection to spendly.db with sane defaults."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create the users and expenses tables if they don't already exist."""
    conn = get_db()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT NOT NULL,
                email         TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at    TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS expenses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                amount      REAL NOT NULL,
                category    TEXT NOT NULL,
                date        TEXT NOT NULL,
                description TEXT,
                created_at  TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users (id)
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def seed_db():
    """Insert one demo user and 8 sample expenses, but only the first time."""
    conn = get_db()
    try:
        existing = conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()
        if existing["count"] > 0:
            return  # already seeded — do nothing

        password_hash = generate_password_hash("demo123", method="pbkdf2:sha256")
        cursor = conn.execute(
            """
            INSERT INTO users (name, email, password_hash)
            VALUES (?, ?, ?)
            """,
            ("Demo User", "demo@spendly.com", password_hash),
        )
        user_id = cursor.lastrowid

        year_month = datetime.now().strftime("%Y-%m")
        sample_expenses = [
            (14.32, "Food", f"{year_month}-01", "Groceries at Trader Joe's"),
            (23.50, "Transport", f"{year_month}-02", "Uber ride to airport"),
            (89.99, "Bills", f"{year_month}-04", "Electricity bill"),
            (15.75, "Health", f"{year_month}-05", "Pharmacy - prescription refill"),
            (32.00, "Entertainment", f"{year_month}-07", "Movie tickets"),
            (78.40, "Shopping", f"{year_month}-08", "New running shoes"),
            (46.20, "Food", f"{year_month}-10", "Dinner at Italian restaurant"),
            (20.00, "Other", f"{year_month}-11", "Charity donation"),
        ]

        conn.executemany(
            """
            INSERT INTO expenses (user_id, amount, category, date, description)
            VALUES (?, ?, ?, ?, ?)
            """,
            [(user_id, amt, cat, dt, desc) for amt, cat, dt, desc in sample_expenses],
        )
        conn.commit()
    finally:
        conn.close()
