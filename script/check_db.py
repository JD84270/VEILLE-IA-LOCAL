import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "veille.db"

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, source_name, block, sub_block, title, status
    FROM items
    ORDER BY id DESC
    """)

    rows = cursor.fetchall()

    print(f"Nombre d'items en base : {len(rows)}")
    print("-" * 80)

    for row in rows:
        print(f"ID        : {row[0]}")
        print(f"Source    : {row[1]}")
        print(f"Bloc      : {row[2]}")
        print(f"Sous-bloc : {row[3]}")
        print(f"Titre     : {row[4]}")
        print(f"Statut    : {row[5]}")
        print("-" * 80)

    conn.close()

if __name__ == "__main__":
    main()