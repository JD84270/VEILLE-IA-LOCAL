from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
FILE_PATH = BASE_DIR / "script" / "generate_dashboard.py"

content = FILE_PATH.read_text(encoding="utf-8")


# -------------------------------------------------------------------
# 0. Compacter les titres des onglets
# -------------------------------------------------------------------
old_labels = '''labels = {
        "stack_technique": "Stack technique",
        "archifact": "ArchiFact",
        "sitenote": "SiteNote",
        "ia_automatisation_saas": "IA automatisation SaaS",
        "ia_ecosysteme": "IA locale & écosystème",
        "business_saas": "Business SaaS",
        "signaux_faibles": "Signaux faibles",
    }'''

new_labels = '''labels = {
        "stack_technique": "Stack",
        "archifact": "ArchiFact",
        "sitenote": "SiteNote",
        "ia_automatisation_saas": "IA SaaS",
        "ia_ecosysteme": "IA locale",
        "business_saas": "Business",
        "signaux_faibles": "Signaux",
    }'''

content = content.replace(old_labels, new_labels)


# -------------------------------------------------------------------
# 1. Modifier render_section pour devenir un contenu d'onglet
# -------------------------------------------------------------------
old_section_start = """    return f\"\"\"
    <section class="section">
      <div class="section-header">
"""

new_section_start = """    return f\"\"\"
    <section class="section tab-content" data-tab="{escape(block)}">
      <div class="section-header">
"""

if old_section_start in content and 'class="section tab-content" data-tab="{escape(block)}"' not in content:
    content = content.replace(old_section_start, new_section_start)


# -------------------------------------------------------------------
# 2. Ajouter fonctions onglets + dashboard synthèse
# -------------------------------------------------------------------
insert_before = """def top_items(rows, limit=3):
"""

tabs_functions = r'''
def rows_for_block(rows, block):
    return [row for row in rows if safe(row[3]).lower().strip() == block]


def get_visible_blocks(rows):
    known = []

    for block in BLOCK_ORDER:
        if rows_for_block(rows, block):
            known.append(block)

    unknown = sorted({
        safe(row[3]).lower().strip()
        for row in rows
        if safe(row[3]).lower().strip()
        and safe(row[3]).lower().strip() not in set(BLOCK_ORDER)
    })

    return known + unknown


def count_by_block(rows, block):
    return len(rows_for_block(rows, block))


def render_tabs(rows):
    blocks = get_visible_blocks(rows)

    html = """
    <nav class="tabs" aria-label="Navigation des blocs de veille">
      <button class="tab-btn active" data-target="dashboard">Dashboard</button>
    """

    for block in blocks:
        count = count_by_block(rows, block)
        html += f"""
      <button class="tab-btn" data-target="{escape(block)}">{escape(block_label(block))} <span>{count}</span></button>
        """

    html += """
    </nav>
    """

    return html


def top_items_by_decision(rows, decision, limit=5):
    filtered = [row for row in rows if row[8] == decision]
    filtered.sort(key=lambda r: (r[9] or 0), reverse=True)
    return filtered[:limit]


def render_dashboard_section(rows):
    groups = []

    for decision in ["AGIR", "TESTER", "SURVEILLER"]:
        items = top_items_by_decision(rows, decision, limit=5)
        if items:
            groups.append(render_decision_group(decision, items))

    groups_html = "\n".join(groups)

    if not groups_html.strip():
        groups_html = """
        <div class="empty-state">
          Aucun signal prioritaire détecté pour le moment.
        </div>
        """

    return f"""
    <section class="section tab-content active" data-tab="dashboard">
      <div class="section-header">
        <div>
          <p class="section-kicker">Vue synthèse</p>
          <h2>Dashboard</h2>
          <p class="section-intro">
            Synthèse courte des signaux les plus importants. Les onglets permettent ensuite d’ouvrir chaque bloc sans scroller toute la veille.
          </p>
        </div>
        <span class="badge ok">Top priorités</span>
      </div>

      {groups_html}
    </section>
    """


'''

if insert_before in content and "def render_tabs(rows):" not in content:
    content = content.replace(insert_before, tabs_functions + insert_before)


# -------------------------------------------------------------------
# 3. Modifier main() pour générer dashboard + onglets
# -------------------------------------------------------------------
old_sections_block = """    sections_html = "\\n".join(
        render_section(block, rows)
        for block in BLOCK_ORDER
    )

    extra_sections_html = render_unknown_blocks(rows)

    if extra_sections_html:
        sections_html += "\\n" + extra_sections_html
"""

new_sections_block = """    sections_html = render_dashboard_section(rows)

    block_sections_html = "\\n".join(
        render_section(block, rows)
        for block in BLOCK_ORDER
    )

    if block_sections_html:
        sections_html += "\\n" + block_sections_html

    extra_sections_html = render_unknown_blocks(rows)

    if extra_sections_html:
        sections_html += "\\n" + extra_sections_html

    tabs_html = render_tabs(rows)
"""

if old_sections_block in content and "tabs_html = render_tabs(rows)" not in content:
    content = content.replace(old_sections_block, new_sections_block)


# -------------------------------------------------------------------
# 4. Injecter les onglets dans le HTML après les KPI
# -------------------------------------------------------------------
old_after_kpis = """    </section>

    <div class="layout">
"""

new_after_kpis = """    </section>

    {tabs_html}

    <div class="layout">
"""

if old_after_kpis in content and "{tabs_html}" not in content:
    content = content.replace(old_after_kpis, new_after_kpis, 1)


# -------------------------------------------------------------------
# 5. CSS onglets — version propre et compacte
# -------------------------------------------------------------------
new_tabs_css = """    .tabs {{
      position: sticky;
      top: 0;
      z-index: 20;
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      padding: 12px;
      margin: 0 0 24px;
      border-radius: 24px;
      background: rgba(255,255,255,0.92);
      border: 1px solid var(--line);
      box-shadow: 0 12px 28px rgba(31,36,48,0.05);
      backdrop-filter: blur(14px);
      overflow: hidden;
    }}

    .tab-btn {{
      flex: 0 0 auto;
      border: 0;
      cursor: pointer;
      padding: 10px 14px;
      border-radius: 999px;
      background: #ffffff;
      border: 1px solid #e4e7f0;
      color: #525a6c;
      font-size: 13px;
      font-weight: 850;
      white-space: nowrap;
    }}

    .tab-btn span {{
      margin-left: 5px;
      color: var(--muted);
      font-weight: 850;
    }}

    .tab-btn.active {{
      background: var(--primary);
      color: #ffffff;
      border-color: var(--primary);
      box-shadow: 0 10px 22px rgba(109,97,236,0.22);
    }}

    .tab-btn.active span {{
      color: rgba(255,255,255,0.82);
    }}

    .tab-content {{
      display: none;
    }}

    .tab-content.active {{
      display: block;
    }}

    .empty-state {{
      padding: 22px;
      border-radius: 24px;
      background: var(--paper-soft);
      border: 1px dashed var(--line);
      color: var(--muted);
      font-weight: 750;
    }}

"""

tabs_start = content.find("    .tabs {{")
tabs_end = content.find("    .layout {{", tabs_start)

if tabs_start != -1 and tabs_end != -1:
    content = content[:tabs_start] + new_tabs_css + content[tabs_end:]
else:
    old_css_anchor = """    .layout {{
      display: grid;
      grid-template-columns: 1fr 340px;
      gap: 24px;
      align-items: start;
    }}
"""
    new_css_anchor = new_tabs_css + old_css_anchor
    if old_css_anchor in content:
        content = content.replace(old_css_anchor, new_css_anchor)


# -------------------------------------------------------------------
# 6. Ajouter JS onglets avant les boutons cards
# -------------------------------------------------------------------
old_js_anchor = """    document.querySelectorAll(".card-actions button").forEach((button) => {{
"""

tabs_js = """    document.querySelectorAll(".tab-btn").forEach((button) => {{
      button.addEventListener("click", () => {{
        const target = button.dataset.target;

        document.querySelectorAll(".tab-btn").forEach((btn) => {{
          btn.classList.remove("active");
        }});

        document.querySelectorAll(".tab-content").forEach((section) => {{
          section.classList.remove("active");
        }});

        button.classList.add("active");

        const activeSection = document.querySelector(`.tab-content[data-tab="${{target}}"]`);
        if (activeSection) {{
          activeSection.classList.add("active");
          window.scrollTo({{ top: 0, behavior: "smooth" }});
        }}
      }});
    }});

"""

if old_js_anchor in content and 'document.querySelectorAll(".tab-btn")' not in content:
    content = content.replace(old_js_anchor, tabs_js + old_js_anchor)


FILE_PATH.write_text(content, encoding="utf-8")
print("Patch onglets appliqué à generate_dashboard.py")