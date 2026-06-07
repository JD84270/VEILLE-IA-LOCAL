import sqlite3
from pathlib import Path
from html import escape
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "veille.db"
DASHBOARD_DIR = BASE_DIR / "dashboard"
DASHBOARD_PATH = DASHBOARD_DIR / "index.html"

DECISION_ORDER = ["AGIR", "TESTER", "SURVEILLER", "LECTURE", "ARCHIVE"]

BLOCK_ORDER = [
    "stack_technique",
    "archifact",
    "sitenote",
    "ia_automatisation_saas",
    "ia_locale_ecosysteme",
    "business_saas",
    "signaux_faibles",
]


def safe(value, fallback=""):
    if value is None:
        return fallback
    value = str(value).strip()
    return value if value else fallback


def get_items():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            status,
            source_name,
            block,
            sub_block,
            priority,
            title,
            url,
            decision,
            score,
            reason,
            recommended_action,
            impact,
            next_step,
            analyzed_at
        FROM items
        WHERE COALESCE(status, 'new') NOT IN ('done', 'archived')
        ORDER BY
            block ASC,
            CASE decision
                WHEN 'AGIR' THEN 1
                WHEN 'TESTER' THEN 2
                WHEN 'SURVEILLER' THEN 3
                WHEN 'LECTURE' THEN 4
                WHEN 'ARCHIVE' THEN 5
                ELSE 6
            END,
            score DESC
    """)

    rows = cursor.fetchall()
    conn.close()
    return rows


def count_by_decision(rows, decision):
    return len([row for row in rows if row[8] == decision])


def avg_score(rows):
    scores = [row[9] for row in rows if row[9] is not None]
    return round(sum(scores) / len(scores), 1) if scores else 0


def signal_score(rows):
    useful = [row for row in rows if row[8] in ["AGIR", "TESTER", "SURVEILLER"]]
    return min(100, round((len(useful) / len(rows)) * 100)) if rows else 0


def decision_class(decision):
    return {
        "AGIR": "action",
        "TESTER": "test",
        "SURVEILLER": "watch",
        "LECTURE": "read",
        "ARCHIVE": "ignore",
    }.get(decision, "ignore")


def priority_label(priority):
    return {
        "critical": "Critique",
        "high": "Haute",
        "medium": "Moyenne",
        "low": "Basse",
    }.get(priority, "Moyenne")


def status_label(status):
    return {
        "new": "Nouveau",
        "viewed": "Lu",
        "in_progress": "En cours",
        "done": "Traité",
        "archived": "Archivé",
    }.get(status, "Nouveau")


def block_label(block):
    block = safe(block, "non_classe").lower().strip()

    labels = {
        "stack_technique": "Stack technique",
        "archifact": "ArchiFact",
        "sitenote": "SiteNote",
        "ia_automatisation_saas": "IA automatisation SaaS",
        "ia_locale_ecosysteme": "IA locale & écosystème",
        "business_saas": "Business SaaS",
        "signaux_faibles": "Signaux faibles",
    }

    return labels.get(block, block.replace("_", " ").title())


def block_intro(block):
    block = safe(block, "non_classe").lower().strip()

    intros = {
        "stack_technique": "Sources critiques liées à l’architecture locale, aux modèles, aux frameworks, aux outils développeur et aux choix techniques.",
        "archifact": "Signaux utiles pour le produit ArchiFact : facturation, honoraires, PDF, SaaS métier, conformité et automatisation.",
        "sitenote": "Signaux utiles pour SiteNote : suivi de chantier, réserves, OPR, terrain, CR, mobilité et ergonomie métier.",
        "ia_automatisation_saas": "Automatisations IA applicables à tes produits SaaS, aux workflows métier et à la productivité.",
        "ia_locale_ecosysteme": "Évolutions de l’IA locale, des modèles open source, de l’infrastructure et des usages hors cloud.",
        "business_saas": "Informations liées au marché SaaS, pricing, acquisition, concurrence, distribution et opportunités commerciales.",
        "signaux_faibles": "Indices émergents, mouvements de fond ou informations encore incertaines mais potentiellement importantes.",
    }

    return intros.get(block, "Sources classées dans ce bloc de veille.")


def render_analysis_block(label, value, css_class=""):
    value = safe(value, "Non renseigné.")
    return f"""
      <div class="analysis-card {css_class}">
        <span>{escape(label)}</span>
        <p>{escape(value)}</p>
      </div>
    """


def render_item(row):
    (
        item_id,
        status,
        source_name,
        block,
        sub_block,
        priority,
        title,
        url,
        decision,
        score,
        reason,
        recommended_action,
        impact,
        next_step,
        analyzed_at,
    ) = row

    status = safe(status, "new")
    decision = safe(decision, "NON ANALYSÉ")
    score = score if score is not None else "-"
    source_name = safe(source_name, "Source inconnue")
    title = safe(title, "Sans titre")
    url = safe(url, "#")
    block = safe(block, "Bloc non classé")
    sub_block = safe(sub_block, "Sous-bloc non classé")
    priority = safe(priority, "medium")

    return f"""
    <article class="item {decision_class(decision)}-item" data-item-id="{escape(str(item_id))}">
      <div class="item-top">
        <div>
          <span class="source">{escape(source_name)}</span>
          <div class="mini-meta">
            <span>{escape(block_label(block))}</span>
            <span>{escape(sub_block)}</span>
            <span>Priorité {escape(priority_label(priority))}</span>
            <span>Statut {escape(status_label(status))}</span>
          </div>
        </div>
        <span class="decision {decision_class(decision)}">{escape(decision)} · score {escape(str(score))}</span>
      </div>

      <h3>{escape(title)}</h3>

      <div class="analysis-grid">
        {render_analysis_block("Pourquoi c’est important", reason, "reason")}
        {render_analysis_block("Action recommandée", recommended_action, "action-box")}
        {render_analysis_block("Impact potentiel", impact, "impact")}
        {render_analysis_block("Prochaine étape", next_step, "next")}
      </div>

      <div class="card-actions">
        <button data-id="{escape(str(item_id))}" data-status="viewed" data-feedback="relevant">Lu</button>
        <button data-id="{escape(str(item_id))}" data-status="in_progress" data-feedback="tested">À tester</button>
        <button data-id="{escape(str(item_id))}" data-status="archived" data-feedback="not_relevant">Pas pertinent</button>
        <button data-id="{escape(str(item_id))}" data-status="done" data-feedback="implemented">Traité</button>
        <button data-id="{escape(str(item_id))}" data-status="archived" data-feedback="archived">Archiver</button>
      </div>

      <div class="item-footer">
        <a class="source-link" href="{escape(url)}" target="_blank" rel="noopener noreferrer">Ouvrir la source</a>
        <span class="analyzed-at">Analysé : {escape(safe(analyzed_at, "date inconnue"))}</span>
      </div>
    </article>
    """


def render_decision_group(decision, rows):
    items = [row for row in rows if row[8] == decision]
    if not items:
        return ""

    title = {
        "AGIR": "À traiter",
        "TESTER": "À tester",
        "SURVEILLER": "À surveiller",
        "LECTURE": "Lecture",
        "ARCHIVE": "Archives",
    }.get(decision, decision)

    intro = {
        "AGIR": "Actions concrètes ou arbitrages rapides.",
        "TESTER": "Nouveautés à expérimenter sans engagement lourd.",
        "SURVEILLER": "Sujets utiles mais encore incertains.",
        "LECTURE": "Informations de contexte sans action immédiate.",
        "ARCHIVE": "Bruit filtré ou éléments peu utiles actuellement.",
    }.get(decision, "")

    badge_css = {
        "AGIR": "critical",
        "TESTER": "watch",
        "SURVEILLER": "watch",
        "LECTURE": "ok",
        "ARCHIVE": "ignore",
    }.get(decision, "ok")

    rendered_items = "\n".join(render_item(row) for row in items)

    return f"""
      <div class="decision-group">
        <div class="decision-group-header">
          <div>
            <h3>{escape(title)}</h3>
            <p>{escape(intro)}</p>
          </div>
          <span class="badge {badge_css}">{escape(decision)} · {len(items)}</span>
        </div>

        {rendered_items}
      </div>
    """


def render_section(block, rows):
    block_rows = [row for row in rows if safe(row[3]).lower().strip() == block]
    if not block_rows:
        return ""

    groups_html = "\n".join(
        render_decision_group(decision, block_rows)
        for decision in DECISION_ORDER
    )

    if not groups_html.strip():
        return ""

    return f"""
    <section class="section">
      <div class="section-header">
        <div>
          <p class="section-kicker">Bloc de veille</p>
          <h2>{escape(block_label(block))}</h2>
          <p class="section-intro">{escape(block_intro(block))}</p>
        </div>
        <span class="badge ok">{len(block_rows)} signal(s)</span>
      </div>

      {groups_html}
    </section>
    """


def render_unknown_blocks(rows):
    known = set(BLOCK_ORDER)
    blocks = sorted({
        safe(row[3]).lower().strip()
        for row in rows
        if safe(row[3]).lower().strip() and safe(row[3]).lower().strip() not in known
    })

    return "\n".join(render_section(block, rows) for block in blocks)


def top_items(rows, limit=3):
    filtered = [row for row in rows if row[8] in ["AGIR", "TESTER", "SURVEILLER"]]
    filtered.sort(key=lambda r: (r[9] or 0), reverse=True)
    return filtered[:limit]


def render_top_list(rows):
    items = top_items(rows)
    if not items:
        return "<li><span class='rank'>1</span><span>Aucun signal prioritaire détecté.</span></li>"

    html = ""
    for index, row in enumerate(items, start=1):
        source = safe(row[2], "Source inconnue")
        decision = safe(row[8], "NON ANALYSÉ")
        next_step = safe(row[13], safe(row[11], "Signal détecté."))
        html += f"""
        <li>
          <span class="rank">{index}</span>
          <span><strong>{escape(decision)}</strong> · {escape(source)} — {escape(next_step)}</span>
        </li>
        """
    return html


def main():
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)

    rows = get_items()
    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    total = len(rows)
    agir = count_by_decision(rows, "AGIR")
    tester = count_by_decision(rows, "TESTER")
    surveiller = count_by_decision(rows, "SURVEILLER")
    lecture = count_by_decision(rows, "LECTURE")
    archive = count_by_decision(rows, "ARCHIVE")
    average = avg_score(rows)
    signal = signal_score(rows)

    sections_html = "\n".join(
        render_section(block, rows)
        for block in BLOCK_ORDER
    )

    extra_sections_html = render_unknown_blocks(rows)

    if extra_sections_html:
        sections_html += "\n" + extra_sections_html

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Veille IA Locale — Dashboard</title>

  <style>
    :root {{
      --bg: #f4f5f9;
      --paper: #ffffff;
      --paper-soft: #fafbff;
      --ink: #1f2430;
      --muted: #747b8f;
      --line: #e4e7f0;
      --primary: #6d61ec;
      --primary-soft: #efedff;
      --danger: #ef7b45;
      --danger-soft: #fff1e9;
      --watch: #d99b22;
      --watch-soft: #fff7e3;
      --good: #2f9e6d;
      --good-soft: #e9f8f1;
      --shadow: 0 20px 50px rgba(31, 36, 48, 0.08);
      --radius-xl: 32px;
      --radius-lg: 24px;
    }}

    * {{ box-sizing: border-box; }}

    body {{
      margin: 0;
      min-height: 100vh;
      background:
        radial-gradient(circle at top left, rgba(109, 97, 236, 0.13), transparent 34%),
        linear-gradient(180deg, #f7f8fc 0%, #eef1f7 100%);
      font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", Roboto, Arial, sans-serif;
      color: var(--ink);
    }}

    .page {{
      width: min(1180px, calc(100% - 44px));
      margin: 0 auto;
      padding: 42px 0 56px;
    }}

    .hero {{
      position: relative;
      overflow: hidden;
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 28px;
      padding: 36px;
      border-radius: var(--radius-xl);
      background:
        linear-gradient(135deg, rgba(255,255,255,0.98), rgba(244,246,255,0.96)),
        radial-gradient(circle at 80% 10%, rgba(109,97,236,0.20), transparent 26%);
      border: 1px solid rgba(228, 231, 240, 0.95);
      box-shadow: var(--shadow);
    }}

    .eyebrow {{
      margin: 0 0 10px;
      font-size: 12px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.14em;
      color: var(--primary);
    }}

    h1 {{
      margin: 0;
      max-width: 760px;
      font-size: clamp(32px, 5vw, 52px);
      line-height: 0.96;
      letter-spacing: -0.055em;
    }}

    .hero-subtitle {{
      max-width: 720px;
      margin: 18px 0 0;
      font-size: 17px;
      line-height: 1.6;
      color: var(--muted);
    }}

    .meta-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 26px;
    }}

    .pill {{
      display: inline-flex;
      padding: 9px 13px;
      border-radius: 999px;
      background: rgba(255,255,255,0.86);
      border: 1px solid var(--line);
      color: #555d72;
      font-size: 13px;
      font-weight: 700;
    }}

    .score-card {{
      min-width: 176px;
      padding: 22px;
      border-radius: 26px;
      background: var(--paper);
      border: 1px solid var(--line);
      box-shadow: 0 14px 34px rgba(31,36,48,0.07);
      text-align: center;
    }}

    .score-card span {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.12em;
    }}

    .score-card strong {{
      display: block;
      margin-top: 8px;
      font-size: 56px;
      line-height: 1;
      color: var(--primary);
      letter-spacing: -0.05em;
    }}

    .score-card small {{
      display: block;
      margin-top: 8px;
      color: var(--muted);
      font-weight: 700;
    }}

    .kpis {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 16px;
      margin: 24px 0;
    }}

    .kpi {{
      padding: 22px;
      border-radius: var(--radius-lg);
      background: rgba(255,255,255,0.92);
      border: 1px solid var(--line);
      box-shadow: 0 10px 26px rgba(31,36,48,0.045);
    }}

    .kpi .label {{
      display: block;
      margin-bottom: 12px;
      color: var(--muted);
      font-size: 13px;
      font-weight: 750;
    }}

    .kpi .value {{
      display: flex;
      align-items: baseline;
      gap: 8px;
      font-size: 36px;
      font-weight: 850;
      letter-spacing: -0.05em;
    }}

    .kpi .value small {{
      font-size: 13px;
      color: var(--muted);
      letter-spacing: 0;
    }}

    .layout {{
      display: grid;
      grid-template-columns: 1fr 340px;
      gap: 24px;
      align-items: start;
    }}

    .section {{
      margin-bottom: 22px;
      padding: 28px;
      border-radius: var(--radius-xl);
      background: rgba(255,255,255,0.96);
      border: 1px solid var(--line);
      box-shadow: 0 16px 38px rgba(31,36,48,0.055);
    }}

    .section-header {{
      display: flex;
      justify-content: space-between;
      align-items: start;
      gap: 18px;
      margin-bottom: 24px;
    }}

    .section-kicker {{
      margin: 0 0 6px;
      color: var(--primary);
      font-size: 12px;
      font-weight: 850;
      text-transform: uppercase;
      letter-spacing: 0.13em;
    }}

    h2 {{
      margin: 0;
      font-size: 25px;
      letter-spacing: -0.035em;
    }}

    .section-intro {{
      margin: 10px 0 0;
      color: var(--muted);
      line-height: 1.55;
    }}

    .decision-group {{
      margin-top: 22px;
      padding-top: 22px;
      border-top: 1px solid #edf0f7;
    }}

    .decision-group:first-of-type {{
      margin-top: 0;
      padding-top: 0;
      border-top: 0;
    }}

    .decision-group-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 16px;
      margin-bottom: 14px;
    }}

    .decision-group-header h3 {{
      margin: 0;
      font-size: 18px;
      letter-spacing: -0.025em;
    }}

    .decision-group-header p {{
      margin: 6px 0 0;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.45;
    }}

    .badge {{
      display: inline-flex;
      align-items: center;
      white-space: nowrap;
      padding: 8px 12px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 850;
    }}

    .badge.critical {{ color: #bf5423; background: var(--danger-soft); }}
    .badge.watch {{ color: #9b6a09; background: var(--watch-soft); }}
    .badge.ok {{ color: #247a55; background: var(--good-soft); }}
    .badge.ignore {{ color: #657084; background: #eef1f6; }}

    .item {{
      padding: 22px;
      border-radius: 24px;
      background: var(--paper-soft);
      border: 1px solid #edf0f7;
    }}

    .item + .item {{ margin-top: 16px; }}

    .item-top {{
      display: flex;
      justify-content: space-between;
      gap: 14px;
      align-items: flex-start;
      margin-bottom: 14px;
    }}

    .source {{
      color: var(--muted);
      font-size: 13px;
      font-weight: 800;
    }}

    .mini-meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 7px;
      margin-top: 8px;
    }}

    .mini-meta span {{
      padding: 6px 9px;
      border-radius: 999px;
      background: var(--primary-soft);
      color: #5f55dc;
      font-size: 11px;
      font-weight: 850;
    }}

    .decision {{
      display: inline-flex;
      align-items: center;
      white-space: nowrap;
      padding: 7px 11px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 850;
    }}

    .decision.action {{ color: #c05224; background: var(--danger-soft); }}
    .decision.test {{ color: #7a4d00; background: var(--watch-soft); }}
    .decision.watch {{ color: #98670b; background: var(--watch-soft); }}
    .decision.read {{ color: #247a55; background: var(--good-soft); }}
    .decision.ignore {{ color: #657084; background: #eef1f6; }}

    .item h3 {{
      margin: 0 0 16px;
      font-size: 20px;
      letter-spacing: -0.03em;
      line-height: 1.25;
    }}

    .analysis-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
      margin-top: 12px;
    }}

    .analysis-card {{
      padding: 15px 16px;
      border-radius: 17px;
      background: #ffffff;
      border: 1px solid #eceef5;
      min-height: 112px;
    }}

    .analysis-card span {{
      display: block;
      margin-bottom: 8px;
      font-size: 12px;
      font-weight: 900;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: #2b3140;
    }}

    .analysis-card p {{
      margin: 0;
      color: #525a6c;
      line-height: 1.52;
      font-size: 14px;
    }}

    .analysis-card.action-box {{
      background: #fffaf1;
      border-color: #f4dfad;
    }}

    .analysis-card.impact {{
      background: #f7f6ff;
      border-color: #dfdcff;
    }}

    .analysis-card.next {{
      background: #f1fbf6;
      border-color: #cdeedd;
    }}

    .item-footer {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 16px;
    }}

    .card-actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 16px;
    }}

    .card-actions button {{
      border: 0;
      cursor: pointer;
      padding: 8px 11px;
      border-radius: 999px;
      background: #ffffff;
      border: 1px solid #e4e7f0;
      color: #525a6c;
      font-size: 12px;
      font-weight: 850;
    }}

    .card-actions button:hover {{
      background: var(--primary-soft);
      color: var(--primary);
    }}

    .source-link {{
      color: var(--primary);
      text-decoration: none;
      font-weight: 850;
      font-size: 13px;
    }}

    .analyzed-at {{
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
    }}

    .side-panel {{
      position: sticky;
      top: 24px;
    }}

    .panel-card {{
      padding: 24px;
      border-radius: var(--radius-xl);
      background: rgba(255,255,255,0.96);
      border: 1px solid var(--line);
      box-shadow: 0 16px 38px rgba(31,36,48,0.055);
      margin-bottom: 18px;
    }}

    .panel-card h2 {{ font-size: 21px; }}

    .priority-list {{
      margin: 18px 0 0;
      padding: 0;
      list-style: none;
    }}

    .priority-list li {{
      display: grid;
      grid-template-columns: 28px 1fr;
      gap: 12px;
      padding: 14px 0;
      border-top: 1px solid #edf0f7;
      color: #525a6c;
      line-height: 1.45;
    }}

    .priority-list li:first-child {{
      border-top: 0;
      padding-top: 0;
    }}

    .rank {{
      width: 28px;
      height: 28px;
      border-radius: 10px;
      display: inline-grid;
      place-items: center;
      background: var(--primary-soft);
      color: var(--primary);
      font-weight: 900;
      font-size: 13px;
    }}

    .footer-note {{
      margin-top: 26px;
      color: var(--muted);
      text-align: center;
      font-size: 13px;
    }}

    @media (max-width: 980px) {{
      .hero, .layout {{ grid-template-columns: 1fr; }}
      .side-panel {{ position: static; }}
      .kpis {{ grid-template-columns: repeat(2, 1fr); }}
    }}

    @media (max-width: 720px) {{
      .analysis-grid {{ grid-template-columns: 1fr; }}
    }}

    @media (max-width: 620px) {{
      .page {{
        width: min(100% - 24px, 1180px);
        padding-top: 18px;
      }}

      .hero, .section, .panel-card {{
        padding: 22px;
        border-radius: 24px;
      }}

      .kpis {{ grid-template-columns: 1fr; }}

      .section-header, .item-top, .decision-group-header {{
        flex-direction: column;
        align-items: flex-start;
      }}
    }}
  </style>
</head>

<body>
  <main class="page">

    <header class="hero">
      <div>
        <p class="eyebrow">Rapport quotidien · Veille IA locale</p>
        <h1>Ce qui mérite ton attention aujourd’hui</h1>
        <p class="hero-subtitle">
          Synthèse priorisée des signaux utiles pour ArchiFact, SiteNote, ta stack technique,
          l’IA locale et les opportunités marché.
        </p>

        <div class="meta-row">
          <span class="pill">{datetime.now().strftime("%A %d %B %Y")}</span>
          <span class="pill">Dernière analyse : {now}</span>
          <span class="pill">{total} sources analysées</span>
          <span class="pill">Mode local</span>
        </div>
      </div>

      <aside class="score-card">
        <span>Signal utile</span>
        <strong>{signal}</strong>
        <small>score journalier</small>
      </aside>
    </header>

    <section class="kpis">
      <article class="kpi action">
        <span class="label">À traiter</span>
        <div class="value">{agir} <small>items</small></div>
      </article>

      <article class="kpi">
        <span class="label">À tester</span>
        <div class="value">{tester} <small>items</small></div>
      </article>

      <article class="kpi watch">
        <span class="label">À surveiller</span>
        <div class="value">{surveiller} <small>items</small></div>
      </article>

      <article class="kpi ignore">
        <span class="label">Ignorés</span>
        <div class="value">{archive} <small>items</small></div>
      </article>
    </section>

    <div class="layout">
      <div>
        {sections_html}
      </div>

      <aside class="side-panel">
        <section class="panel-card">
          <p class="section-kicker">Synthèse IA</p>
          <h2>Top priorités</h2>
          <ul class="priority-list">
            {render_top_list(rows)}
          </ul>
        </section>

        <section class="panel-card">
          <p class="section-kicker">Indicateurs</p>
          <h2>Vue rapide</h2>
          <ul class="priority-list">
            <li><span class="rank">A</span><span>Score moyen : <strong>{average}/10</strong></span></li>
            <li><span class="rank">B</span><span>Lecture : <strong>{lecture}</strong> item(s)</span></li>
            <li><span class="rank">C</span><span>Total analysé : <strong>{total}</strong> item(s)</span></li>
          </ul>
        </section>

        <section class="panel-card">
          <p class="section-kicker">Règle de tri</p>
          <h2>Décision</h2>
          <p class="section-intro">
            Une information mérite d’être affichée si elle change une décision,
            confirme une hypothèse importante ou révèle un risque concret.
          </p>
        </section>
      </aside>
    </div>

    <p class="footer-note">
      Dashboard généré localement · SQLite + Ollama · Données réelles injectées depuis veille.db
    </p>

  </main>
    <script>
    document.querySelectorAll(".card-actions button").forEach((button) => {{
      button.addEventListener("click", async () => {{
        const id = button.dataset.id;
        const status = button.dataset.status;
        const feedback = button.dataset.feedback;

        try {{
          const response = await fetch("http://127.0.0.1:5000/update-status", {{
            method: "POST",
            headers: {{
              "Content-Type": "application/json"
            }},
            body: JSON.stringify({{ id, status, feedback }})
          }});

          const result = await response.json();

          if (!result.ok) {{
            alert("Erreur lors de la mise à jour.");
            return;
          }}

          const card = button.closest(".item");

          if (status === "done" || status === "archived") {{
            card.remove();
          }} else {{
            button.textContent = button.textContent + " ✓";
          }}
        }} catch (error) {{
          alert("Serveur local non lancé. Lance dashboard_server.py.");
        }}
      }});
    }});
  </script>

</body>

</html>
"""

    DASHBOARD_PATH.write_text(html, encoding="utf-8")
    print(f"Dashboard premium généré : {DASHBOARD_PATH}")


if __name__ == "__main__":
    main()
