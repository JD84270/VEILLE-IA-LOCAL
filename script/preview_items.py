import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "veille.db"


def clean(text):
    if not text:
        return ""
    return " ".join(str(text).split())


def print_stats(cursor):
    print("\n" + "=" * 120)
    print("STATS BASE")
    print("=" * 120)

    cursor.execute("""
    SELECT status, COUNT(*)
    FROM items
    GROUP BY status
    ORDER BY status
    """)

    rows = cursor.fetchall()

    if not rows:
        print("Aucun item.")
    else:
        for status, count in rows:
            print(f"{status or 'NULL':<12} : {count}")

    print("-" * 120)

    cursor.execute("""
    SELECT decision, COUNT(*)
    FROM items
    WHERE status = 'analyzed'
    GROUP BY decision
    ORDER BY
        CASE decision
            WHEN 'AGIR' THEN 1
            WHEN 'TESTER' THEN 2
            WHEN 'SURVEILLER' THEN 3
            WHEN 'LECTURE' THEN 4
            WHEN 'ARCHIVE' THEN 5
            ELSE 6
        END
    """)

    rows = cursor.fetchall()

    if rows:
        print("Décisions analysées :")
        for decision, count in rows:
            print(f"{decision or 'NULL':<12} : {count}")

    print("-" * 120)

    cursor.execute("""
    SELECT source_name, COUNT(*)
    FROM items
    WHERE status = 'new'
    GROUP BY source_name
    ORDER BY COUNT(*) DESC, source_name ASC
    LIMIT 15
    """)

    rows = cursor.fetchall()

    if rows:
        print("Sources avec le plus d'items NEW :")
        for source_name, count in rows:
            print(f"{source_name:<35} : {count}")

    print("=" * 120 + "\n")


def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print_stats(cursor)

    cursor.execute("""
    SELECT
        id,
        source_name,
        block,
        sub_block,
        priority,
        status,
        decision,
        score,
        title,
        summary,
        reason,
        recommended_action,
        impact,
        next_step,
        analyzed_at
    FROM items
    ORDER BY id DESC
    LIMIT 80
    """)

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("Aucun item trouvé.")
        return

    for row in rows:
        (
            item_id,
            source_name,
            block,
            sub_block,
            priority,
            status,
            decision,
            score,
            title,
            summary,
            reason,
            action,
            impact,
            next_step,
            analyzed_at
        ) = row

        print("=" * 120)
        print(f"ID        : {item_id}")
        print(f"Source    : {source_name}")
        print(f"Bloc      : {block} / {sub_block}")
        print(f"Priorité  : {priority}")
        print(f"Status    : {status}")
        print(f"Decision  : {decision or '-'}")
        print(f"Score     : {score if score is not None else '-'}")
        print(f"Analysé   : {analyzed_at or '-'}")
        print(f"Titre     : {clean(title)}")
        print("-" * 120)

        print("Résumé collecté :")
        print(clean(summary)[:1200] or "Aucun résumé.")
        print()

        if reason or action or impact or next_step:
            print("Analyse IA :")
            print(f"Pourquoi   : {clean(reason) or '-'}")
            print(f"Action     : {clean(action) or '-'}")
            print(f"Impact     : {clean(impact) or '-'}")
            print(f"Next step  : {clean(next_step) or '-'}")
            print()

    print("=" * 120)
    print(f"{len(rows)} item(s) affiché(s).")


if __name__ == "__main__":
    main()