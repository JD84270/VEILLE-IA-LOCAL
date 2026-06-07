from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
FILE_PATH = BASE_DIR / "script" / "generate_dashboard.py"

content = FILE_PATH.read_text(encoding="utf-8")

# 1. Ajout HTML boutons
old_footer = """      <div class="item-footer">
        <a class="source-link" href="{escape(url)}" target="_blank" rel="noopener noreferrer">Ouvrir la source</a>
        <span class="analyzed-at">Analysé : {escape(safe(analyzed_at, "date inconnue"))}</span>
      </div>
"""

new_footer = """      <div class="card-actions">
        <button data-id="{escape(str(item_id))}" data-status="viewed">Lu</button>
        <button data-id="{escape(str(item_id))}" data-status="in_progress">En cours</button>
        <button data-id="{escape(str(item_id))}" data-status="done">Traité</button>
        <button data-id="{escape(str(item_id))}" data-status="archived">Archiver</button>
      </div>

      <div class="item-footer">
        <a class="source-link" href="{escape(url)}" target="_blank" rel="noopener noreferrer">Ouvrir la source</a>
        <span class="analyzed-at">Analysé : {escape(safe(analyzed_at, "date inconnue"))}</span>
      </div>
"""

if old_footer in content and "card-actions" not in content:
    content = content.replace(old_footer, new_footer)

# 2. Ajout CSS
old_css = """    .item-footer {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 16px;
    }}
"""

new_css = """    .item-footer {{
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
"""

if old_css in content and ".card-actions {{" not in content:
    content = content.replace(old_css, new_css)

# 3. Ajout JS avant </body>
script = """  <script>
    document.querySelectorAll(".card-actions button").forEach((button) => {
      button.addEventListener("click", async () => {
        const id = button.dataset.id;
        const status = button.dataset.status;

        try {
          const response = await fetch("http://127.0.0.1:5000/update-status", {
            method: "POST",
            headers: {
              "Content-Type": "application/json"
            },
            body: JSON.stringify({ id, status })
          });

          const result = await response.json();

          if (!result.ok) {
            alert("Erreur lors de la mise à jour.");
            return;
          }

          const card = button.closest(".item");

          if (status === "done" || status === "archived") {
            card.remove();
          } else {
            button.textContent = button.textContent + " ✓";
          }
        } catch (error) {
          alert("Serveur local non lancé. Lance dashboard_server.py.");
        }
      });
    });
  </script>

</body>
"""

if "update-status" not in content:
    content = content.replace("</body>", script)

FILE_PATH.write_text(content, encoding="utf-8")
print("Boutons ajoutés dans generate_dashboard.py")