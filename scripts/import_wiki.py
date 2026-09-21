"""Import public pages from the authorized source wiki into editable JSON files.

Run this manually only when a fresh snapshot is wanted. Existing local edits are
kept unless --overwrite is supplied.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
API = "https://churchofgod.wiki/api.php"
ORIGIN = "https://churchofgod.wiki"
MAIN_TITLE = "하나님의 교회 지식사전"
HEADERS = {"User-Agent": "ChurchWikiStaticArchive/1.0 (authorized site migration)"}


def api(params: dict, attempts: int = 4) -> dict:
    params = {"format": "json", "formatversion": "2", **params}
    for attempt in range(attempts):
        try:
            response = requests.get(API, params=params, headers=HEADERS, timeout=45)
            response.raise_for_status()
            data = json.loads(response.content.decode("utf-8"))
            if "error" in data:
                raise RuntimeError(data["error"])
            return data
        except (requests.RequestException, ValueError, RuntimeError):
            if attempt + 1 == attempts:
                raise
            time.sleep(2 ** attempt)
    raise AssertionError("unreachable")


def all_pages() -> list[dict]:
    result = []
    continuation = {}
    while True:
        data = api({"action": "query", "list": "allpages", "aplimit": "max", "apnamespace": 0, **continuation})
        result.extend(data["query"]["allpages"])
        continuation = data.get("continue", {})
        if not continuation:
            break
    return result


def absolutize_media(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(True):
        for attr in ("src", "poster", "data-src"):
            value = tag.get(attr)
            if value and (value.startswith("/") or value.startswith("//")):
                tag[attr] = urljoin(ORIGIN, value)
        if tag.get("srcset"):
            tag["srcset"] = ", ".join(
                urljoin(ORIGIN, part.strip().split()[0]) + " " + " ".join(part.strip().split()[1:])
                for part in tag["srcset"].split(",") if part.strip()
            )
        if tag.name == "a" and tag.get("href", "").startswith("/images/"):
            tag["href"] = urljoin(ORIGIN, tag["href"])
    for tag in soup.select(".mw-editsection, .mw-empty-elt"):
        tag.decompose()
    return str(soup)


def import_page(page: dict, overwrite: bool) -> tuple[str, str]:
    page_id = str(page["pageid"])
    target = ROOT / "content" / "pages" / f"imported-{int(page_id) % 12:02d}" / f"{page_id}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not overwrite:
        return page_id, "existing"
    parsed = api({"action": "parse", "pageid": page["pageid"], "prop": "text|categories|sections|displaytitle"})["parse"]
    body = absolutize_media(parsed["text"])
    soup = BeautifulSoup(body, "html.parser")
    summary = ""
    for para in soup.find_all("p"):
        candidate = para.get_text(" ", strip=True)
        if len(candidate) >= 35:
            summary = candidate[:220]
            break
    record = {
        "title": parsed["title"],
        "summary": summary,
        "categories": [x["category"].replace("_", " ") for x in parsed.get("categories", []) if not x.get("hidden")],
        "body": body,
        "source_url": f"{ORIGIN}/{requests.utils.quote(parsed['title'].replace(' ', '_'), safe='')}",
    }
    target.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return page_id, "written"


def import_shell() -> None:
    response = requests.get(f"{ORIGIN}/{requests.utils.quote(MAIN_TITLE.replace(' ', '_'), safe='')}", headers=HEADERS, timeout=45)
    response.raise_for_status()
    html = response.content.decode("utf-8")
    soup = BeautifulSoup(html, "html.parser")
    shell = ROOT / "site" / "shell.html"
    shell.parent.mkdir(parents=True, exist_ok=True)
    shell.write_text(str(soup), encoding="utf-8")
    css_dir = ROOT / "site" / "assets" / "css"
    css_dir.mkdir(parents=True, exist_ok=True)
    for index, link in enumerate(soup.select('link[rel="stylesheet"]')):
        url = urljoin(ORIGIN, link.get("href", ""))
        if not url.startswith(ORIGIN):
            continue
        data = requests.get(url, headers=HEADERS, timeout=45)
        data.raise_for_status()
        css = data.content.decode("utf-8")
        css = re.sub(r"url\((['\"]?)(?!data:|https?:)([^)'\"]+)\1\)",
                     lambda m: f"url({urljoin(url, m.group(2))})", css)
        (css_dir / f"source-{index}.css").write_text(css, encoding="utf-8")
    logo = requests.get(f"{ORIGIN}/resources/assets/ko/logo.png", headers=HEADERS, timeout=30)
    logo.raise_for_status()
    (ROOT / "site" / "assets" / "logo.png").write_bytes(logo.content)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    (ROOT / "content" / "pages").mkdir(parents=True, exist_ok=True)
    import_shell()
    pages = all_pages()
    recent_data = api({"action": "query", "list": "recentchanges", "rcnamespace": 0, "rclimit": 50, "rcprop": "title"})
    recent_titles = list(dict.fromkeys(item["title"] for item in recent_data["query"]["recentchanges"]))
    (ROOT / "content" / "recent.json").write_text(json.dumps(recent_titles, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.limit:
        pages = pages[:args.limit]
    print(f"Importing {len(pages)} pages", flush=True)
    counts = {"written": 0, "existing": 0, "failed": 0}
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(import_page, page, args.overwrite): page for page in pages}
        for index, future in enumerate(concurrent.futures.as_completed(futures), 1):
            try:
                _, status = future.result()
                counts[status] += 1
            except Exception as exc:
                counts["failed"] += 1
                print(f"FAILED {futures[future]['title']}: {exc}", flush=True)
            if index % 50 == 0 or index == len(pages):
                print(f"{index}/{len(pages)} {counts}", flush=True)
    if counts["failed"]:
        raise SystemExit(f"Import incomplete: {counts['failed']} pages failed")


if __name__ == "__main__":
    main()
