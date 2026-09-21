"""Save the four front-page images locally for stable GitHub Pages hosting."""

import json
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "content" / "pages"
ASSETS = ROOT / "site" / "assets"

for path in PAGES.glob("*.json"):
    page = json.loads(path.read_text(encoding="utf-8"))
    if page["title"] == "하나님의 교회 지식사전":
        break
else:
    raise SystemExit("Homepage not found")

urls = list(dict.fromkeys(img["src"] for img in BeautifulSoup(page["body"], "html.parser").select("img[src]")))
mapping = {}
for number, url in enumerate(urls):
    extension = ".png" if ".png" in url.lower() else ".jpg"
    filename = f"home-{number}{extension}"
    response = requests.get(url, timeout=45)
    response.raise_for_status()
    (ASSETS / filename).write_bytes(response.content)
    mapping[url] = filename
    print(filename, len(response.content))
(ASSETS / "home-images.json").write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
