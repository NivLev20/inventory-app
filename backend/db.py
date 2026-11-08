"""
Database layer.

In production (Docker / Kubernetes) the app talks to PostgreSQL.
In unit tests (CI pipeline) it uses a temporary SQLite file, so tests run
fast without needing a real database server.

The switch is controlled by the DATABASE_URL environment variable:
    postgresql://user:pass@host:5432/dbname  -> PostgreSQL
    sqlite:///path/to/file.db                -> SQLite
"""
import os
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime

from flask import g, current_app

STARTUP_LOCK_ID = 727001  # any fixed number; identifies our startup lock

POSTGRES_SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS products (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        sku TEXT NOT NULL UNIQUE,
        category TEXT NOT NULL DEFAULT 'General',
        store TEXT NOT NULL DEFAULT 'Main',
        price NUMERIC(10, 2) NOT NULL DEFAULT 0,
        stock INTEGER NOT NULL DEFAULT 0,
        min_stock INTEGER NOT NULL DEFAULT 10,
        created_at TIMESTAMP NOT NULL,
        updated_at TIMESTAMP NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS restock_logs (
        id SERIAL PRIMARY KEY,
        product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
        quantity INTEGER NOT NULL,
        stock_before INTEGER NOT NULL,
        stock_after INTEGER NOT NULL,
        note TEXT,
        created_at TIMESTAMP NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS stock_history (
        id SERIAL PRIMARY KEY,
        product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
        stock INTEGER NOT NULL,
        reason TEXT NOT NULL,
        created_at TIMESTAMP NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sales (
        id SERIAL PRIMARY KEY,
        product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
        quantity INTEGER NOT NULL,
        created_at TIMESTAMP NOT NULL
    )
    """,
    # Analytics filters these tables by date; the simulator adds thousands of rows a day
    "CREATE INDEX IF NOT EXISTS idx_sales_created ON sales (created_at)",
    "CREATE INDEX IF NOT EXISTS idx_restock_logs_created ON restock_logs (created_at)",
    "CREATE INDEX IF NOT EXISTS idx_stock_history_created ON stock_history (created_at)",
    "CREATE INDEX IF NOT EXISTS idx_stock_history_product ON stock_history (product_id, id)",
]

SQLITE_SCHEMA = [
    s.replace("SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT")
    for s in POSTGRES_SCHEMA
]


def database_url():
    return current_app.config.get("DATABASE_URL") or os.environ.get(
        "DATABASE_URL", "sqlite:///inventory.db"
    )


def is_postgres():
    return database_url().startswith("postgres")


def _connect():
    url = database_url()
    if url.startswith("postgres"):
        import psycopg2  # imported only when needed
        import psycopg2.extras

        conn = psycopg2.connect(url, connect_timeout=5)
        conn.cursor_factory = psycopg2.extras.RealDictCursor
        return conn

    path = url.replace("sqlite:///", "", 1)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db():
    if "db" not in g:
        g.db = _connect()
    return g.db


def close_db(_exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def _sql(query):
    # SQLite uses "?" placeholders, PostgreSQL uses "%s"
    return query.replace("?", "%s") if is_postgres() else query


def day_of(column):
    """SQL expression for the calendar day of a timestamp column, as YYYY-MM-DD."""
    return f"CAST({column} AS DATE)" if is_postgres() else f"substr({column}, 1, 10)"


def _row_to_dict(row):
    if row is None:
        return None
    result = dict(row)
    for key, value in result.items():
        if isinstance(value, (datetime, date)):
            result[key] = value.isoformat()
        elif value.__class__.__name__ == "Decimal":
            result[key] = float(value)
    return result


def query_all(query, params=()):
    cur = get_db().cursor()
    cur.execute(_sql(query), params)
    rows = [_row_to_dict(r) for r in cur.fetchall()]
    cur.close()
    return rows


def query_one(query, params=()):
    cur = get_db().cursor()
    cur.execute(_sql(query), params)
    row = _row_to_dict(cur.fetchone())
    cur.close()
    return row


def execute(query, params=(), returning_id=False):
    conn = get_db()
    cur = conn.cursor()
    if returning_id:
        query = query.rstrip() + " RETURNING id"
    cur.execute(_sql(query), params)
    new_id = cur.fetchone()["id"] if returning_id else None
    cur.close()
    if not g.get("in_transaction"):
        conn.commit()
    return new_id


@contextmanager
def transaction():
    """Run several statements as one unit: all are committed, or none are."""
    conn = get_db()
    g.in_transaction = True
    try:
        yield
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        g.in_transaction = False


def is_integrity_error(exc):
    """True for unique / foreign key violations from either database driver."""
    return isinstance(exc, sqlite3.IntegrityError) or exc.__class__.__name__ in (
        "IntegrityError", "UniqueViolation", "ForeignKeyViolation")


def init_db():
    conn = get_db()
    cur = conn.cursor()
    for statement in (POSTGRES_SCHEMA if is_postgres() else SQLITE_SCHEMA):
        cur.execute(statement)
    conn.commit()
    cur.close()


def get_setting(key, default=None):
    row = query_one("SELECT value FROM settings WHERE key = ?", (key,))
    return row["value"] if row else default


def set_setting(key, value):
    # Upsert syntax supported by both PostgreSQL and SQLite
    execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT (key) DO UPDATE SET value = excluded.value",
        (key, value),
    )


@contextmanager
def startup_lock():
    """Cluster-wide lock for startup work, using a PostgreSQL advisory lock.

    When two backend replicas start together, both would try to create tables
    and insert demo data at the same time, and one would crash on a duplicate.
    With the lock, the second replica waits, then sees the work is already done.
    SQLite (tests) has a single process, so no lock is needed there.
    """
    if not is_postgres():
        yield
        return
    execute("SELECT pg_advisory_lock(?)", (STARTUP_LOCK_ID,))
    try:
        yield
    finally:
        # If the startup work failed, the transaction is aborted and must be cleared
        # before the unlock can run; otherwise the original error would be hidden.
        get_db().rollback()
        execute("SELECT pg_advisory_unlock(?)", (STARTUP_LOCK_ID,))


def ping():
    cur = get_db().cursor()
    cur.execute("SELECT 1")
    cur.fetchone()
    cur.close()
