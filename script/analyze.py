import re
import sqlite3
import subprocess
import os
import time
import yaml
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "veille.db"
USER_CONTEXT_PATH = BASE_DIR / "user_context.yaml"

OLLAMA_MODEL = "qwen3-coder:30b"
ANALYZE_LIMIT = 20
OLLAMA_TIMEOUT = 180
SUMMARY_LIMIT = 1500


def sanitize_text(text):
    if not text:
        return ""

    text = str(text)
    text = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text)
    text = re.sub(r"\[[0-9A-Fa-f]{1,4}[A-Za-z]?\]", "", text)
    text = text.replace("�", "")
    text = text.replace("\x08", "")
    text = re.sub(r"[\x00-\x1F\x7F]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def load_user_context():
    if not USER_CONTEXT_PATH.exists():
        return "Aucun contexte utilisateur disponible."

    with open(USER_CONTEXT_PATH, "r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    return yaml.dump(data, allow_unicode=True, sort_keys=False)


def get_items_to_analyze(limit=ANALYZE_LIMIT):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, source_name, block, sub_block, priority, title, summary
    FROM items
    WHERE COALESCE(status, 'new') = 'new'
      AND COALESCE(status, 'new') NOT IN ('done', 'archived', 'error')
    ORDER BY
        CASE priority
            WHEN 'critical' THEN 1
            WHEN 'high' THEN 2
            WHEN 'medium' THEN 3
            WHEN 'low' THEN 4
            ELSE 5
        END,
        id ASC
    LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    return rows


def ask_ollama(item):
    item_id, source_name, block, sub_block, priority, title, summary = item
    user_context = load_user_context()

    title = sanitize_text(title)
    summary = sanitize_text(summary)

    prompt = f"""
Tu es un analyste de veille stratégique pour JD.

Contexte utilisateur :
{user_context}

JD développe deux produits SaaS :
- ArchiFact : propositions d’honoraires, notes d’honoraires, facturation métier architectes / BET / MOE.
- SiteNote : suivi de chantier, OPR, réserves, remarques, documents, comptes rendus.

Objectif :
Classer l’information suivante pour un dashboard de veille.

Catégories possibles :
AGIR
TESTER
SURVEILLER
LECTURE
ARCHIVE

Définitions strictes :
- AGIR = action concrète à faire maintenant, car risque réel et direct sur production, sécurité, conformité, paiement, facture électronique, coût ou obligation.
- TESTER = nouveauté disponible et concrète à essayer, avec gain probable pour ArchiFact, SiteNote, IA locale, dev, UX ou productivité.
- SURVEILLER = sujet intéressant mais pas encore applicable, pas urgent, impact incertain, ou à revoir plus tard.
- LECTURE = utile pour culture, inspiration, compréhension marché, sans action concrète.
- ARCHIVE = bruit, marketing, page produit, page catégorie, contenu trop générique ou sans impact.

Règles très importantes :
- Ne classe AGIR que si une action technique, réglementaire ou produit doit réellement être faite maintenant.
- Une source critical ne suffit jamais à justifier AGIR.
- Une page générale Stripe, DGFIP, Pennylane, Indy, Deltek ou autre ne doit pas devenir AGIR sans changement précis et applicable.
- Stripe = AGIR uniquement si breaking change, webhook, checkout, subscription, paiement, API version obligatoire, sécurité ou incident production.
- DGFIP / facturation électronique = AGIR uniquement si nouvelle échéance, obligation, plateforme agréée, calendrier officiel, format, e-reporting ou impact direct ArchiFact.
- Page produit, page marketing, landing page, support, conférence, podcast, page catégorie = ARCHIVE ou LECTURE.
- Si l’action recommandée est vague comme “évaluer”, “suivre”, “se renseigner”, “faire une veille”, alors ce n’est pas AGIR.
- Si l’information est déjà connue ou générale, classe SURVEILLER ou LECTURE.
- Pour AGIR, le score doit être 8, 9 ou 10.
- Pour TESTER, le score doit être 6, 7 ou 8.
- Pour SURVEILLER, le score doit être 4 à 7.
- Pour LECTURE, le score doit être 2 à 5.
- Pour ARCHIVE, le score doit être 1 à 3.

Format obligatoire :
Réponds strictement avec ces 6 lignes, sans JSON, sans markdown :

DECISION: une des catégories
SCORE: un nombre de 1 à 10
RAISON: pourquoi cette information mérite ou non l'attention de JD
ACTION: action recommandée principale, ou "Aucune"
IMPACT: impact potentiel sur ArchiFact, SiteNote, la stack, les coûts ou la productivité
NEXT_STEP: prochaine étape concrète, simple et exécutable

Source : {source_name}
Bloc : {block}
Sous-bloc : {sub_block}
Priorité : {priority}
Titre : {title}

Contenu :
{summary[:SUMMARY_LIMIT]}
"""

    process = subprocess.Popen(
        ["ollama", "run", OLLAMA_MODEL],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )

    try:
        stdout, stderr = process.communicate(
            input=prompt,
            timeout=OLLAMA_TIMEOUT
        )
    except subprocess.TimeoutExpired:
        if process.poll() is None:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            else:
                process.kill()
        process.communicate()
        raise RuntimeError(
            f"Timeout Ollama apres {OLLAMA_TIMEOUT} secondes pour l'item {item_id}"
        )

    if process.returncode != 0:
        stderr_clean = sanitize_text(stderr)
        if not stderr_clean:
            stderr_clean = "Aucun message stderr"
        raise RuntimeError(
            f"Ollama a echoue avec returncode={process.returncode} : {stderr_clean}"
        )

    return stdout.strip()


def extract_field(response, field_name):
    labels = ["DECISION", "SCORE", "RAISON", "ACTION", "IMPACT", "NEXT_STEP"]
    other_labels = [label for label in labels if label != field_name]

    pattern = rf"{field_name}\s*:\s*(.*?)(?=\s*(?:{'|'.join(other_labels)})\s*:|$)"
    match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)

    if not match:
        return ""

    value = match.group(1).strip()
    value = re.split(r"\bDECISION\s*:", value, flags=re.IGNORECASE)[0]

    return sanitize_text(value)


def parse_response(response):
    raw_response = response or ""

    decision_positions = [
        match.start()
        for match in re.finditer(r"\bDECISION\s*:", raw_response, re.IGNORECASE)
    ]

    if len(decision_positions) >= 2:
        raw_response = raw_response[decision_positions[0]:decision_positions[1]]
    elif len(decision_positions) == 1:
        raw_response = raw_response[decision_positions[0]:]

    response_clean = raw_response.strip()

    decision = "ARCHIVE"
    score = 1

    decision_match = re.search(
        r"DECISION\s*:\s*(AGIR|TESTER|SURVEILLER|LECTURE|ARCHIVE)",
        response_clean,
        re.IGNORECASE
    )

    score_match = re.search(
        r"SCORE\s*:\s*([0-9]{1,2})",
        response_clean,
        re.IGNORECASE
    )

    if decision_match:
        decision = decision_match.group(1).strip().upper()

    if score_match:
        try:
            score = int(score_match.group(1))
        except ValueError:
            score = 1

    reason = extract_field(response_clean, "RAISON")
    action = extract_field(response_clean, "ACTION")
    impact = extract_field(response_clean, "IMPACT")
    next_step = extract_field(response_clean, "NEXT_STEP")

    score = max(1, min(score, 10))

    return {
        "decision": decision,
        "score": score,
        "reason": sanitize_text(reason),
        "recommended_action": sanitize_text(action),
        "impact": sanitize_text(impact),
        "next_step": sanitize_text(next_step)
    }


def post_filter(item, analysis):
    item_id, source_name, block, sub_block, priority, title, summary = item

    title_l = sanitize_text(title).lower()
    summary_l = sanitize_text(summary).lower()
    action_l = analysis["recommended_action"].lower()
    blob = f"{title_l} {summary_l}"

    vague_actions = [
        "évaluer",
        "evaluer",
        "suivre",
        "surveiller",
        "se renseigner",
        "identifier",
        "faire une veille",
        "analyser",
        "étudier",
        "etudier",
    ]

    marketing_titles = [
        "podcast",
        "conference",
        "aia26",
        "fireside",
        "support",
        "dirigeants",
        "qui sommes-nous",
        "news",
        "compte pro",
        "comptabilité en ligne",
        "déclaration",
        "track projects",
        "project accounting",
        "meet dela",
        "harmony",
        "users conference",
    ]

    agir_keywords = [
        "breaking change",
        "security",
        "sécurité",
        "incident",
        "obligatoire",
        "obligation",
        "deadline",
        "échéance",
        "migration",
        "webhook",
        "checkout",
        "subscription",
        "api version",
        "facturation électronique",
        "plateforme agréée",
        "e-reporting",
        "factur-x",
        "rls",
        "auth",
        "passkeys",
    ]

    tester_keywords = [
        "beta",
        "preview",
        "available",
        "nouveau",
        "new",
        "agent",
        "agents",
        "automation",
        "workflow",
        "claude code",
        "lm studio",
        "cursor",
        "codex",
        "figma",
        "api",
    ]

    if any(word in title_l for word in marketing_titles):
        if analysis["decision"] in {"AGIR", "TESTER"}:
            analysis["decision"] = "LECTURE"
            analysis["score"] = min(analysis["score"], 4)

    if analysis["decision"] == "AGIR":
        has_real_agir_signal = any(word in blob for word in agir_keywords)
        has_vague_action = any(word in action_l for word in vague_actions)

        if not has_real_agir_signal or has_vague_action:
            analysis["decision"] = "SURVEILLER"
            analysis["score"] = min(analysis["score"], 6)

    if analysis["decision"] == "TESTER":
        has_test_signal = any(word in blob for word in tester_keywords)

        if not has_test_signal and priority not in {"critical", "high"}:
            analysis["decision"] = "SURVEILLER"
            analysis["score"] = min(analysis["score"], 6)

    if analysis["decision"] == "AGIR" and analysis["score"] < 8:
        analysis["score"] = 8

    if analysis["decision"] == "TESTER" and analysis["score"] > 8:
        analysis["score"] = 8

    if analysis["decision"] == "SURVEILLER" and analysis["score"] > 7:
        analysis["score"] = 7

    if analysis["decision"] == "LECTURE" and analysis["score"] > 5:
        analysis["score"] = 5

    if analysis["decision"] == "ARCHIVE" and analysis["score"] > 3:
        analysis["score"] = 3

    if analysis["decision"] == "AGIR" and analysis["recommended_action"].lower() == "aucune":
        analysis["decision"] = "SURVEILLER"
        analysis["score"] = min(analysis["score"], 6)

    return analysis


def update_item(item_id, analysis):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE items
    SET
        status = 'analyzed',
        decision = ?,
        score = ?,
        reason = ?,
        recommended_action = ?,
        impact = ?,
        next_step = ?,
        analyzed_at = ?
    WHERE id = ?
    """, (
        analysis["decision"],
        analysis["score"],
        analysis["reason"],
        analysis["recommended_action"],
        analysis["impact"],
        analysis["next_step"],
        datetime.now().isoformat(),
        item_id
    ))

    conn.commit()
    conn.close()


def mark_error(item_id, error_message):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE items
    SET
        status = 'error',
        reason = ?,
        analyzed_at = ?
    WHERE id = ?
    """, (
        sanitize_text(f"Erreur analyse : {error_message}")[:500],
        datetime.now().isoformat(),
        item_id
    ))

    conn.commit()
    conn.close()


def main():
    start_time = time.monotonic()
    analyzed_count = 0
    error_count = 0

    items = get_items_to_analyze(limit=ANALYZE_LIMIT)

    if not items:
        print("Aucun item à analyser.", flush=True)
        return

    for item in items:
        item_id = item[0]
        source_name = item[1]
        priority = item[4]

        print(f"Analyse item {item_id} - {source_name} [{priority}]", flush=True)

        try:
            response = ask_ollama(item)
            analysis = parse_response(response)
            analysis = post_filter(item, analysis)
            update_item(item_id, analysis)
            analyzed_count += 1

            print(f"Décision : {analysis['decision']}", flush=True)
            print(f"Score    : {analysis['score']}", flush=True)
            print(f"Raison   : {analysis['reason']}", flush=True)
            print(f"Action   : {analysis['recommended_action']}", flush=True)
            print(f"Impact   : {analysis['impact']}", flush=True)
            print(f"Next     : {analysis['next_step']}", flush=True)
            print("-" * 80, flush=True)

        except Exception as error:
            mark_error(item_id, error)
            error_count += 1
            print(f"ERREUR analyse item {item_id} : {error}", flush=True)
            print("Item marqué en status = error", flush=True)
            print("-" * 80, flush=True)

    duration = time.monotonic() - start_time
    print(
        f"Résumé analyse : {analyzed_count} analysé(s), "
        f"{error_count} erreur(s), durée {duration:.1f}s",
        flush=True
    )


if __name__ == "__main__":
    main()
