from pathlib import Path
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
SOURCES_PATH = BASE_DIR / "sources.yaml"

def main():
    if not SOURCES_PATH.exists():
        print(f"Fichier introuvable : {SOURCES_PATH}")
        return

    with open(SOURCES_PATH, "r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    sources = data.get("sources", [])

    print(f"Nombre de sources trouvées : {len(sources)}")
    print("-" * 50)

    for source in sources:
        print(f"Nom       : {source.get('name')}")
        print(f"Bloc      : {source.get('block')}")
        print(f"Sous-bloc : {source.get('sub_block')}")
        print(f"Type      : {source.get('type')}")
        print(f"URL       : {source.get('url')}")
        print("-" * 50)

if __name__ == "__main__":
    main()