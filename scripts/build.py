"""Build the editable static wiki for GitHub Pages."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dist"
ORIGIN = "churchofgod.wiki"
MAIN_TITLE = "하나님의 교회 지식사전"


def key(title: str) -> str:
    return title.replace("_", " ").strip().casefold()


def read_pages() -> list[dict]:
    result = []
    for path in sorted((ROOT / "content" / "pages").rglob("*.json")):
        item = json.loads(path.read_text(encoding="utf-8"))
        if not item.get("title") or not item.get("body"):
            raise ValueError(f"Missing title/body: {path}")
        item["_file"] = path.stem
        item["_source_path"] = path.relative_to(ROOT).as_posix()
        result.append(item)
    return result


def href_for(raw: str, prefix: str, titles: dict[str, str]) -> str:
    if not raw or raw.startswith(("#", "mailto:", "tel:", "javascript:")):
        return raw
    parsed = urlparse(raw)
    if parsed.netloc and parsed.netloc != ORIGIN:
        return raw
    if not parsed.netloc and not raw.startswith("/"):
        return raw
    path = unquote(parsed.path).lstrip("/").replace("_", " ")
    if path == "index.php":
        path = parse_qs(parsed.query).get("title", [""])[0].replace("_", " ")
    if key(path) in (key(MAIN_TITLE), key("대문")):
        return prefix + "index.html"
    if key(path) in (key("최근 문서"), key("최근 문서 보기")):
        return prefix + "recent.html"
    if path in ("특수:모든문서", "Special:AllPages"):
        return prefix + "allpages.html"
    if path in ("특수:최근바뀜", "Special:RecentChanges"):
        return prefix + "recent.html"
    if path in ("특수:임의문서", "Special:Random"):
        return prefix + "random.html"
    if path in ("특수:특수문서", "Special:SpecialPages"):
        return prefix + "special.html"
    if path.startswith(("분류:", "Category:")):
        name = path.split(":", 1)[1]
        return prefix + "category.html?name=" + quote(name)
    article = titles.get(key(path))
    if article:
        return prefix + f"wiki/{article}/"
    if parsed.netloc:
        return raw
    return "https://" + ORIGIN + raw


def localize_links(soup: BeautifulSoup, prefix: str, titles: dict[str, str], local_images: dict[str, str]) -> None:
    for anchor in soup.find_all("a", href=True):
        anchor["href"] = href_for(anchor["href"], prefix, titles)
    for image in soup.find_all("img", src=True):
        if image["src"] in local_images:
            image["src"] = prefix + "assets/" + local_images[image["src"]]
            image.attrs.pop("srcset", None)
        elif image["src"].startswith("/media/"):
            image["src"] = prefix + image["src"].lstrip("/")
        elif image["src"].startswith("/"):
            image["src"] = "https://" + ORIGIN + image["src"]


def set_categories(soup: BeautifulSoup, categories: list[str], prefix: str) -> None:
    box = soup.select_one("#catlinks")
    if box is None:
        return
    box.clear()
    if not categories:
        box.decompose()
        return
    label = soup.new_tag("span")
    label.string = "분류: "
    box.append(label)
    for i, name in enumerate(categories):
        if i:
            box.append(" · ")
        link = soup.new_tag("a", href=prefix + "category.html?name=" + quote(name))
        link.string = name
        box.append(link)


def render(shell: str, title: str, body: str, prefix: str, titles: dict[str, str], local_images: dict[str, str],
           categories: list[str] | None = None, edit_file: str | None = None, description: str = "") -> str:
    soup = BeautifulSoup(shell, "html.parser")
    for script in soup.find_all("script"):
        script.decompose()
    for link in soup.select('link[rel="stylesheet"]'):
        link.decompose()
    for link in soup.select('link[rel="preload"], link[rel="modulepreload"]'):
        link.decompose()
    for link in soup.select('link[rel="canonical"]'):
        link.decompose()
    for meta in soup.head.select('meta[property^="og:"], meta[name^="twitter:"], meta[name="description"]'):
        meta.decompose()
    if soup.head:
        for i in range(5):
            link = soup.new_tag("link", rel="stylesheet", href=prefix + f"assets/css/source-{i}.css")
            soup.head.append(link)
        soup.head.append(soup.new_tag("link", rel="stylesheet", href=prefix + "assets/css/local.css"))
        soup.head.append(soup.new_tag("script", src=prefix + "assets/site.js", defer=True))
        viewport = soup.head.select_one('meta[name="viewport"]')
        if viewport:
            viewport["content"] = "width=device-width, initial-scale=1"
        else:
            soup.head.append(soup.new_tag("meta", attrs={"name": "viewport", "content": "width=device-width, initial-scale=1"}))
        summary_text = description or (title + " 문서를 읽어보세요.")
        soup.head.append(soup.new_tag("meta", attrs={"name": "description", "content": summary_text}))
        soup.head.append(soup.new_tag("meta", attrs={"property": "og:title", "content": title}))
        soup.head.append(soup.new_tag("meta", attrs={"property": "og:description", "content": summary_text}))
    if soup.title:
        soup.title.string = title + " - 하나님의 교회 지식사전"
    heading = soup.select_one("#firstHeading")
    if heading:
        heading.string = title
    content = soup.select_one("#mw-content-text")
    if content is None:
        raise ValueError("Source shell has no #mw-content-text")
    content.clear()
    fragment = BeautifulSoup(body, "html.parser")
    for unsafe in fragment.select("script, object, embed"):
        unsafe.decompose()
    for tag in fragment.find_all(True):
        for attr in list(tag.attrs):
            if attr.lower().startswith("on"):
                del tag[attr]
            elif attr.lower() in ("href", "src") and str(tag[attr]).strip().lower().startswith("javascript:"):
                del tag[attr]
    for item in list(fragment.contents):
        content.append(item)
    set_categories(soup, categories or [], prefix)
    localize_links(soup, prefix, titles, local_images)
    search = soup.select_one("#searchform")
    if search:
        search["action"] = prefix + "search.html"
        search["method"] = "get"
        for hidden in search.select('input[type="hidden"]'):
            hidden.decompose()
        field = search.select_one('input[type="search"]')
        if field:
            field["name"] = "q"
    logo = soup.select_one(".mw-wiki-logo")
    if logo:
        logo["href"] = prefix + "index.html"
    panel = soup.select_one("#mw-panel")
    head = soup.select_one("#mw-head")
    if panel and head:
        mobile_nav = soup.new_tag("details", attrs={"class": "local-mobile-nav"})
        summary = soup.new_tag("summary")
        summary.string = "둘러보기"
        mobile_nav.append(summary)
        for original in panel.select("a[href]"):
            link = soup.new_tag("a", href=original.get("href", "#"))
            link.string = original.get_text(" ", strip=True)
            if link.string:
                mobile_nav.append(link)
        head.append(mobile_nav)
    login = soup.select_one("#pt-login a")
    if login:
        login["href"] = "https://app.pagescms.org/"
        login.string = "문서 관리"
    if edit_file:
        content_sub = soup.select_one("#contentSub")
        if content_sub:
            edit = soup.new_tag("a", href=f"https://github.com/donggil113/churchofgod-wiki/edit/main/{edit_file}")
            edit["class"] = "local-edit-link"
            edit.string = "이 문서 편집"
            content_sub.append(edit)
    return str(soup)


def page_list_body(pages: list[dict], prefix: str) -> str:
    grouped: dict[str, list[dict]] = {}
    for page in sorted(pages, key=lambda x: x["title"].casefold()):
        first = page["title"][0].upper()
        grouped.setdefault(first, []).append(page)
    parts = ['<div class="mw-parser-output local-list"><p>모든 문서 목록</p>']
    for letter, group in grouped.items():
        parts.append(f"<h2>{letter}</h2><ul>")
        for page in group:
            parts.append(f'<li><a href="{prefix}wiki/{page["_file"]}/">{escape(page["title"])}</a></li>')
        parts.append("</ul>")
    parts.append("</div>")
    return "".join(parts)


def escape(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def main() -> None:
    pages = read_pages()
    titles = {key(page["title"]): page["_file"] for page in pages}
    local_images = json.loads((ROOT / "site" / "assets" / "home-images.json").read_text(encoding="utf-8"))
    shell = (ROOT / "site" / "shell.html").read_text(encoding="utf-8")
    if not titles.get(key(MAIN_TITLE)):
        raise ValueError(f"Missing homepage: {MAIN_TITLE}")
    if OUT.resolve().parent != ROOT.resolve() or OUT.name != "dist":
        raise ValueError("Refusing to replace a build directory outside this project")
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(ROOT / "site" / "assets", OUT / "assets")
    if (ROOT / "media").exists():
        shutil.copytree(ROOT / "media", OUT / "media")
    (OUT / ".nojekyll").touch()
    (OUT / "wiki").mkdir()
    home = next(page for page in pages if key(page["title"]) == key(MAIN_TITLE))
    (OUT / "index.html").write_text(render(shell, home["title"], home["body"], "", titles, local_images, home.get("categories"), home["_source_path"], home.get("summary", "")), encoding="utf-8")
    for page in pages:
        target = OUT / "wiki" / page["_file"]
        target.mkdir()
        target.joinpath("index.html").write_text(render(shell, page["title"], page["body"], "../../", titles, local_images, page.get("categories"), page["_source_path"], page.get("summary", "")), encoding="utf-8")
    (OUT / "allpages.html").write_text(render(shell, "모든 문서 목록", page_list_body(pages, ""), "", titles, local_images), encoding="utf-8")
    (OUT / "search.html").write_text(render(shell, "검색", '<div class="mw-parser-output local-results" id="local-results"></div>', "", titles, local_images), encoding="utf-8")
    (OUT / "category.html").write_text(render(shell, "분류", '<div class="mw-parser-output local-results" id="local-category"></div>', "", titles, local_images), encoding="utf-8")
    (OUT / "random.html").write_text(render(shell, "임의 문서", '<div class="mw-parser-output"><p>문서를 여는 중입니다.</p></div>', "", titles, local_images), encoding="utf-8")
    special_body = '<div class="mw-parser-output"><ul><li><a href="allpages.html">모든 문서 목록</a></li><li><a href="recent.html">최근 문서</a></li><li><a href="random.html">임의 문서</a></li><li><a href="search.html">검색</a></li></ul></div>'
    (OUT / "special.html").write_text(render(shell, "특수 문서 목록", special_body, "", titles, local_images), encoding="utf-8")
    recent_path = ROOT / "content" / "recent.json"
    recent_titles = json.loads(recent_path.read_text(encoding="utf-8")) if recent_path.exists() else []
    recent = [next((p for p in pages if key(p["title"]) == key(title)), None) for title in recent_titles]
    recent = [p for p in recent if p]
    if not recent:
        recent = pages[:30]
    (OUT / "recent.html").write_text(render(shell, "최근 문서", page_list_body(recent, ""), "", titles, local_images), encoding="utf-8")
    index = [{"id": p["_file"], "title": p["title"], "summary": p.get("summary", ""), "categories": p.get("categories", [])} for p in pages]
    (OUT / "articles.json").write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Built {len(pages)} editable articles into {OUT}")


if __name__ == "__main__":
    main()
