import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "veille.db"

BAD_TITLE_PATTERNS = [
    "%Qui sommes-nous%",
    "%Dirigeants | Pennylane%",
    "%Pennylane News%",
    "%Support Pennylane%",
    "%Facturation électronique - Axonaut%",
    "%Tous nos conseils et astuces%",
    "%Don't Miss the 2026 Ajera Users Conference%",
    "%Ajera Time & Expense%",
    "%Maximize Your Deltek Ajera%",
    "%Your Most Critical Security Control%",
    "%Government Pricing%",
    "%QMS for Aerospace%",
    "%ERP for Government Contractors%",
    "%Experience Deltek Harmony%",
    "%Meet Dela%",
    "%Exclusive Fireside Chats%",
    "%AIA26%",
    "%Entrée Architect Podcast%",
    "%Les Agit'Acteurs%",
    "%IMPACT Tour de France%",
    "%Arnaud Alavant%",
    "%Compte pro 100% gratuit%",
    "%Déclaration : solution automatisée%",
    "%La comptabilité en ligne automatisée%",
    "%Qualibat, partenaire d’EnerJ%",
    "%Retour sur la table ronde de QUALIBAT%",
    "%CSTB - Notre approche%",
    "%CSTB - Toutes les offres%",
    "%CSTB - Pilotage%",
    "%Bâtiments et quartiers%",
    "%Build budgets%",
    "%Assign staff%",
    "%Track projects%",
    "%Project accounting%",
    "%Payment Analytics Dashboard%",
    "%Website Checkout%",
    "%SaaS Subscription Management Software%",
    "%SaaS Billing Software%",
    "%Invoicing Software | Paddle%",
]

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

deleted = 0

for pattern in BAD_TITLE_PATTERNS:
    cursor.execute("""
    DELETE FROM items
    WHERE status = 'new'
      AND title LIKE ?
    """, (pattern,))
    deleted += cursor.rowcount

conn.commit()
conn.close()

print(f"{deleted} item(s) supprimé(s).")