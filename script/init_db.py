import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "veille.db"


def column_exists(cursor, table_name, column_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    return any(column[1] == column_name for column in columns)


def add_column_if_missing(cursor, table_name, column_name, column_sql):
    if not column_exists(cursor, table_name, column_name):
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}")
        print(f"Colonne {column_name} ajoutée.")


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_name TEXT NOT NULL,
        block TEXT NOT NULL,
        sub_block TEXT NOT NULL,
        priority TEXT DEFAULT 'medium',
        title TEXT NOT NULL,
        url TEXT NOT NULL UNIQUE,
        published_at TEXT,
        summary TEXT,
        raw_content TEXT,
        status TEXT DEFAULT 'new',
        decision TEXT,
        score INTEGER,
        reason TEXT,
        recommended_action TEXT,
        impact TEXT,
        next_step TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        analyzed_at TEXT
    );
    """)

    add_column_if_missing(cursor, "items", "priority", "priority TEXT DEFAULT 'medium'")
    add_column_if_missing(cursor, "items", "impact", "impact TEXT")
    add_column_if_missing(cursor, "items", "next_step", "next_step TEXT")

    conn.commit()
    conn.close()

    print(f"Base SQLite prête ici : {DB_PATH}")


if __name__ == "__main__":
    init_db()