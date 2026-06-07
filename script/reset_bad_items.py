import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "veille.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
UPDATE items
SET
    status = 'new',
    decision = NULL,
    score = NULL,
    reason = NULL,
    recommended_action = NULL,
    impact = NULL,
    next_step = NULL,
    analyzed_at = NULL
WHERE recommended_action LIKE '%DECISION%'
""")

conn.commit()
print(f"{cursor.rowcount} item(s) remis à zéro.")
conn.close()