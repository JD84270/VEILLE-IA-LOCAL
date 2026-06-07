import re
import sqlite3
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin, urlparse, quote
import urllib.request
import yaml
from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).resolve().parent.parent
SOURCES_PATH = BASE_DIR / "sources.yaml"
DB_PATH = BASE_DIR / "data" / "veille.db"

MAX_ARTICLES_PER_SOURCE = 5
MIN_ARTICLE_TEXT_LENGTH = 500


BAD_TITLE_KEYWORDS = [
    "archives", "blog -", "blog de", "blog di",
    "fieldwire construction blog", "thinkproject field manager",
    "tous nos", "tous les articles", "conseils et guides",
    "les métiers du btp", "gestion d'entreprise", "devis & facture",
    "réglementation - blog", "social et formation",
    "catégorie", "category", "ressources", "resources",
    "dirigeants", "pennylane news", "pennylane blog",
    "facturation -", "modèles facturation", "règles de facturation",
    "comparateurs", "actualités du btp",
    "ajera | deltek", "business insights", "digital transformation",
    "security & compliance", "workforce management",
    "compte pro", "comptabilité en ligne", "déclaration :",
    "j'adhère", "linda dininger", "author", "auteur",
    "support pennylane",
    "project accounting", "track projects", "assign staff", "build budgets",
    "experience harmony", "meet dela",
    "users conference", "conference", "podcast",
    "fireside chats", "aia26",
    "government pricing", "qms for aerospace",
    "erp for government contractors",
    "logiciel devis", "fonctions clés",
    "monograph",
    "saas billing software", "saas subscription management software",
    "website checkout", "payment analytics dashboard", "invoicing software",
    "cstb - notre approche", "cstb - toutes les offres",
    "cstb - pilotage", "bâtiments et quartiers",
    "enerj", "salon", "inscriptions sont ouvertes",
]


BAD_CONTENT_SIGNALS = [
    "tous les articles",
    "trier les plus récents",
    "trier les plus anciens",
    "titre a-z",
    "titre z-a",
    "nos catégories",
    "voir plus",
    "quel est votre besoin ?",
    "0 résultat(s) trouvé(s)",
    "accéder à la e-boutique",
]


MARKETING_SIGNALS = [
    "get a demo", "book a demo", "watch a tour", "try for free",
    "learn more", "contact us", "request a demo", "start free",
    "free trial", "schedule a demo", "speak to sales", "speak to an expert",
    "sign up now", "get started", "watch overview",
    "démarrer maintenant", "demander une démo", "démo gratuite",
    "essayer gratuitement", "voir les tarifs", "contactez-nous",
    "prendre rendez-vous", "ouvrez votre compte", "s'abonner",
    "noté 5 sur 5", "trustpilot", "app store", "play store",
    "thank you! your submission has been received",
    "oops! something went wrong",
]


PRODUCT_PAGE_SIGNALS = [
    "fonctionnalités", "bénéfices", "pourquoi", "notre solution",
    "nos services", "nos produits", "tarifs", "pricing", "features",
    "product", "solution", "platform", "customer-reported improvements",
    "on average", "customers achieve", "trusted by",
    "unlock", "launch", "turn subscription", "billing solution",
    "checkout", "subscription management",
]


GOOD_CONTENT_SIGNALS = [
    "publié", "published", "updated", "last updated",
    "min read", "temps de lecture",
    "facturation électronique", "plateforme agréée",
    "supabase", "stripe", "weweb",
    "architect", "architecture", "engineering",
    "construction", "chantier", "bureau d'études",
    "bim", "ai", "ia", "agent", "automation",
    "workflow", "invoice", "billing",
    "churn", "retention", "project management",
    "time tracking", "daily report", "rfi",
    "plans", "réserves", "opr",
]


FORCE_KEEP_KEYWORDS = [
    "supabase", "stripe", "weweb",
    "breaking change", "security", "sécurité",
    "auth", "passkeys", "temporary token", "database access",
    "facturation électronique", "plateforme agréée",
    "pdp", "pa ", "factur-x", "e-reporting",
    "architect kpi", "engineering kpi", "engineering invoices",
    "scope changes", "time tracking for architects",
    "daily report", "field-built", "office-first",
    "bim construction", "claude code", "lm studio", "cursor",
    "phishing",
]


def fetch_url(url):
    parsed = urlparse(url)
    safe_path = quote(parsed.path, safe="/%")
    safe_query = quote(parsed.query, safe="=&?")
    safe_url = parsed._replace(path=safe_path, query=safe_query).geturl()

    request = urllib.request.Request(
        safe_url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8", errors="ignore")


def normalize_url(url):
    return url.split("#")[0].strip().rstrip("/")


def clean_html(html):
    soup = BeautifulSoup(html, "lxml")

    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg", "form"]):
        tag.decompose()

    title = soup.title.string.strip() if soup.title and soup.title.string else "Sans titre"

    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines()]
    clean_lines = [line for line in lines if line]

    clean_text = "\n".join(clean_lines)

    clean_text = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", clean_text)
    clean_text = re.sub(r"\[[0-9A-Fa-f]{1,4}[A-Za-z]?\]", "", clean_text)
    clean_text = clean_text.replace("�", "")
    clean_text = re.sub(r"[^\S\r\n]+", " ", clean_text)
    clean_text = re.sub(r"\n{3,}", "\n\n", clean_text)

    title = title.replace("�", "").strip()

    return title, clean_text


def contains_any(text, keywords):
    text = (text or "").lower()
    return any(keyword.lower() in text for keyword in keywords)


def signal_count(text, signals):
    text = (text or "").lower()
    return sum(1 for signal in signals if signal.lower() in text)


def useful_text_ratio(text):
    words = re.findall(r"\b\w+\b", (text or "").lower())

    if not words:
        return 0

    return len(set(words)) / len(words)


def force_keep(title, text):
    blob = f"{title} {text}".lower()
    return contains_any(blob, FORCE_KEEP_KEYWORDS)


def is_quality_item(title, text):
    title_clean = (title or "").lower().strip()
    text_clean = (text or "").lower().strip()
    full_text = f"{title_clean} {text_clean}"

    if not title_clean or title_clean == "sans titre":
        return False

    if len(title_clean.split()) <= 2:
        return False

    if contains_any(title_clean, BAD_TITLE_KEYWORDS):
        return False

    if contains_any(text_clean, BAD_CONTENT_SIGNALS):
        return False

    marketing = signal_count(full_text, MARKETING_SIGNALS)
    product = signal_count(full_text, PRODUCT_PAGE_SIGNALS)
    good = signal_count(full_text, GOOD_CONTENT_SIGNALS)

    if force_keep(title_clean, text_clean):
        return len(text_clean) >= MIN_ARTICLE_TEXT_LENGTH

    if marketing >= 2:
        return False

    if product >= 3:
        return False

    if marketing >= 1 and product >= 1:
        return False

    if useful_text_ratio(text_clean) < 0.18:
        return False

    if good == 0:
        return False

    if len(text_clean) < MIN_ARTICLE_TEXT_LENGTH:
        return False

    return True


def is_bad_url(href_lower):
    bad_patterns = [
        "login", "signin", "sign-in", "signup", "subscribe",
        "contact", "demo", "pricing", "tarifs", "privacy",
        "terms", "legal", "mentions", "newsletter",
        "category", "categories", "tag/", "tags/",
        "author/", "auteur/",
        "facebook", "linkedin", "twitter", "x.com",
        "youtube", "instagram", "trustpilot", "avis",
        "customers", "customer", "clients", "case-studies",
        "webinar", "event", "events", "agenda",
        "fonctionnalites", "features",
        "product", "solutions", "platform",
    ]

    return any(pattern in href_lower for pattern in bad_patterns)


def is_probable_article_link(base_url, href, text):
    if not href:
        return False

    href = normalize_url(href)
    text = (text or "").strip()

    if len(text) < 12:
        return False

    parsed = urlparse(href)

    if parsed.scheme not in ["http", "https", ""]:
        return False

    href_lower = href.lower()

    if is_bad_url(href_lower):
        return False

    article_patterns = [
        "/blog/",
        "/news/",
        "/actualites/",
        "/actualite/",
        "/articles/",
        "/article/",
        "/edito/",
        "/post/",
        "/posts/",
        "/changelog/",
        "/release/",
        "/releases/",
    ]

    if any(pattern in href_lower for pattern in article_patterns):
        return True

    date_patterns = [
        r"/20[0-9]{2}/",
        r"/[0-9]{4}/[0-9]{2}/",
        r"/[0-9]{4}-[0-9]{2}-[0-9]{2}",
    ]

    if any(re.search(pattern, href_lower) for pattern in date_patterns):
        return True

    return False


def extract_article_links(html, base_url):
    soup = BeautifulSoup(html, "lxml")
    links = []

    base_domain = urlparse(base_url).netloc.replace("www.", "")

    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, a.get("href"))
        href = normalize_url(href)
        text = " ".join(a.get_text(separator=" ").split())

        domain = urlparse(href).netloc.replace("www.", "")

        if domain and domain != base_domain:
            continue

        if not is_probable_article_link(base_url, href, text):
            continue

        links.append({
            "url": href,
            "title": text
        })

    seen = set()
    unique_links = []

    for link in links:
        if link["url"] in seen:
            continue

        seen.add(link["url"])
        unique_links.append(link)

    return unique_links[:MAX_ARTICLES_PER_SOURCE]


def item_exists(source_name, url):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id
    FROM items
    WHERE source_name = ?
      AND url = ?
    LIMIT 1
    """, (source_name, url))

    exists = cursor.fetchone() is not None
    conn.close()
    return exists


def save_item(source, title, clean_text, item_url):
    if not is_quality_item(title, clean_text):
        print(f"SKIP qualité - {title[:80]}")
        return False

    if item_exists(source.get("name"), item_url):
        print("SKIP - déjà présent")
        return False

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    summary = clean_text[:1200]
    priority = source.get("priority", "medium")

    cursor.execute("""
    INSERT INTO items (
        source_name,
        block,
        sub_block,
        priority,
        title,
        url,
        published_at,
        summary,
        raw_content,
        status,
        created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        source.get("name"),
        source.get("block"),
        source.get("sub_block"),
        priority,
        title,
        item_url,
        datetime.now().isoformat(),
        summary,
        clean_text,
        "new",
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()
    return True


def collect_source(source):
    name = source.get("name")
    url = source.get("url")
    priority = source.get("priority", "medium")
    source_type = source.get("type", "webpage")

    print(f"Collecte : {name} [{priority}]")

    html = fetch_url(url)

    if source_type == "github_releases":
        title, clean_text = clean_html(html)
        saved = save_item(source, title, clean_text, url)
        if saved:
            print(f"OK page GitHub - {len(clean_text)} caractères utiles")
        return

    article_links = extract_article_links(html, url)
    saved_count = 0

    for link in article_links:
        try:
            article_html = fetch_url(link["url"])
            article_title, article_text = clean_html(article_html)

            final_title = article_title if article_title != "Sans titre" else link["title"]

            saved = save_item(source, final_title, article_text, link["url"])

            if saved:
                saved_count += 1
                print(f"OK article - {final_title[:80]}")

        except Exception as error:
            print(f"ERREUR article : {link['url']} / {error}")

    if saved_count == 0:
        title, clean_text = clean_html(html)
        saved = save_item(source, title, clean_text, url)

        if saved:
            print(f"OK fallback page - {len(clean_text)} caractères utiles")
    else:
        print(f"OK - {saved_count} article(s) collecté(s)")


def main():
    with open(SOURCES_PATH, "r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    sources = data.get("sources", [])

    print(f"Sources à collecter : {len(sources)}")

    for source in sources:
        try:
            collect_source(source)
        except Exception as error:
            print(f"ERREUR : {source.get('name')} / {error}")

    print("Collecte terminée.")


if __name__ == "__main__":
    main()