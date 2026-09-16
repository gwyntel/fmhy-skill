#!/usr/bin/env python3
"""
FMHY Atlas -- ingestion layer.

Turns FMHY's *own machine-readable sources* into a structured, AI-ingestible
reference tree:

    data/raw/                  cached raw snapshot (gitignored)
    references/<class>/<page>.md   one file per FMHY page
    manifest.json              one record per page
    links.jsonl                one record per link occurrence

Canonical sources (see README.md "Source selection"):
  * github.com/fmhy/edit  -- the upstream repo whose docs/*.md files ARE the
    wiki pages.  scripts/generate-single-page.js in that repo concatenates a
    fixed list of these files to produce api.fmhy.net/single-page, so the repo
    is the per-page source of record and the single-page endpoint is a derived
    concatenation of it.
  * https://fmhy.net/sitemap.xml -- canonical page list + public URLs.
  * docs/.vitepress/shared.ts    -- FMHY's own top-level taxonomy (the sidebar).

Design constraints this script honours:
  * Idempotent + cached: a fresh cache means zero network calls.
  * Rate limited to <= 1 HTTP request/second.
  * Descriptive User-Agent naming this project.
  * robots.txt is fetched and obeyed for every HTTP request to FMHY's hosts.
  * No requests are ever made to the third-party sites FMHY links out to.

Usage:
    python3 build.py                # build, refetching only if cache is stale
    python3 build.py --refresh      # force a refetch of the upstream snapshot
    python3 build.py --offline      # build from cache, fail if no cache
    python3 build.py --ttl 0        # treat any cache as stale
    python3 build.py --with-prose   # include non-link prose (see LICENCE note)
    python3 build.py --verify-single-page   # cross-check against the API mirror
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent
RAW_DIR = REPO_ROOT / "data" / "raw"
UPSTREAM_DIR = RAW_DIR / "fmhy-edit"
SNAPSHOT_FILE = RAW_DIR / "snapshot.json"
SITEMAP_FILE = RAW_DIR / "sitemap.xml"
ROBOTS_FILE = RAW_DIR / "robots.txt"
SINGLE_PAGE_FILE = RAW_DIR / "single-page.md"

REFERENCES_DIR = REPO_ROOT / "references"
MANIFEST_FILE = REPO_ROOT / "manifest.json"
LINKS_FILE = REPO_ROOT / "links.jsonl"

UPSTREAM_REPO = "https://github.com/fmhy/edit.git"
UPSTREAM_REPO_WEB = "https://github.com/fmhy/edit"
UPSTREAM_BRANCH = "main"
SITE_ORIGIN = "https://fmhy.net"

#: Must identify the project and give a contact route. Kept short and honest.
USER_AGENT = (
    "FMHY-Atlas/0.1 (non-commercial reference indexer; "
    "indexes FMHY's public link catalogue; +https://github.com/GwynTel/fmhy-skill)"
)

#: At most one HTTP request per second.
RATE_LIMIT_SECONDS = 1.0

#: Default cache lifetime before we go back to the network.
DEFAULT_TTL_SECONDS = 24 * 60 * 60

#: Pages FMHY's build config deliberately keeps out of the published site
#: (docs/.vitepress/shared.ts -> `excluded`).  We still index their source so
#: the repo is complete, and mark them in the manifest.
UPSTREAM_EXCLUDED_FROM_SITE = {
    "readme.md",
    "single-page",
    "single-page.md",
    "feedback.md",
    "index.md",
    "sandbox.md",
    "startpage.md",
}

#: Class used for pages FMHY does not list in its sidebar at all.
FALLBACK_CLASS = "site"

#: FMHY sprinkles U+2060 / U+200B into link text as a rendering workaround.
INVISIBLE_CHARS_RE = re.compile("[\u2060\u200b\u200c\u200d\ufeff]")

#: Namespace / schema URLs that appear in inline SVG and are not links to anything.
IGNORED_URL_PREFIXES = ("http://www.w3.org/", "https://www.w3.org/")

#: FMHY's own section/heading markers, stripped when deriving a display title.
MARKER_RE = re.compile(r"^[\s►▷▪●◆★⭐↪️\u2b1a]*")


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------


def log(msg: str) -> None:
    print(msg, flush=True)


def utcnow() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slugify(value: str) -> str:
    value = INVISIBLE_CHARS_RE.sub("", value)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"[^\w\s-]", "", value, flags=re.UNICODE)
    value = re.sub(r"[\s_]+", "-", value.strip())
    return re.sub(r"-{2,}", "-", value).strip("-").lower()


def strip_html(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", value)).strip()


def display_title(value: str) -> str:
    """FMHY's label or heading text, minus its section markers and emoji."""
    value = INVISIBLE_CHARS_RE.sub("", value)
    value = MARKER_RE.sub("", value)
    value = re.sub(r"^[\W_]+", "", value) if not value[:1].isalnum() else value
    return re.sub(r"\s+", " ", value).strip()


# --------------------------------------------------------------------------
# robots.txt
# --------------------------------------------------------------------------


class RobotsPolicy:
    """Minimal robots.txt matcher: longest-match wins, `*` wildcard, `$` anchor."""

    def __init__(self, text: str, user_agent: str = USER_AGENT):
        self.groups: list[tuple[list[str], list[tuple[str, str]]]] = []
        self.user_agent = user_agent
        self._parse(text)

    def _parse(self, text: str) -> None:
        agents: list[str] = []
        rules: list[tuple[str, str]] = []
        for raw in text.splitlines():
            line = raw.split("#", 1)[0].strip()
            if not line or ":" not in line:
                continue
            field, _, value = line.partition(":")
            field = field.strip().lower()
            value = value.strip()
            if field == "user-agent":
                if rules:
                    self.groups.append((agents, rules))
                    agents, rules = [], []
                agents.append(value.lower())
            elif field in ("allow", "disallow") and agents:
                rules.append((field, value))
        if agents:
            self.groups.append((agents, rules))

    def _rules_for_me(self) -> list[tuple[str, str]]:
        ua = self.user_agent.lower()
        best: list[tuple[str, str]] = []
        best_len = -1
        for agents, rules in self.groups:
            for agent in agents:
                if agent == "*":
                    length = 0
                elif agent in ua:
                    length = len(agent)
                else:
                    continue
                if length >= best_len:
                    best_len = length
                    best = rules
        return best

    @staticmethod
    def _matches(pattern: str, path: str) -> bool:
        if not pattern:
            return False
        anchored = pattern.endswith("$")
        pattern = pattern[:-1] if anchored else pattern
        regex = "^" + re.escape(pattern).replace(r"\*", ".*")
        regex += "$" if anchored else ""
        return re.match(regex, path) is not None

    def allowed(self, url: str) -> bool:
        path = urllib.parse.urlsplit(url).path or "/"
        best_len = -1
        verdict = True
        for field, pattern in self._rules_for_me():
            if self._matches(pattern, path):
                length = len(pattern)
                if length >= best_len:
                    best_len = length
                    verdict = field == "allow"
        return verdict


class Fetcher:
    """Rate-limited, robots-aware HTTP GET with descriptive User-Agent."""

    def __init__(self, robots: RobotsPolicy | None, rate_limit: float = RATE_LIMIT_SECONDS):
        self.robots = robots
        self.rate_limit = rate_limit
        self._last = 0.0
        self.request_count = 0

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last
        if self._last and elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self._last = time.monotonic()

    def get(self, url: str) -> bytes:
        if self.robots is not None and not self.robots.allowed(url):
            raise RuntimeError(f"robots.txt disallows fetching {url}")
        self._throttle()
        log(f"  GET {url}")
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml,text/markdown,text/plain,*/*",
                "From": "fmhy-atlas reference indexer",
            },
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
        self.request_count += 1
        return data


# --------------------------------------------------------------------------
# Snapshot acquisition
# --------------------------------------------------------------------------


def read_snapshot() -> dict | None:
    if not SNAPSHOT_FILE.exists():
        return None
    try:
        return json.loads(SNAPSHOT_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def snapshot_age(snapshot: dict) -> float:
    captured = snapshot.get("captured_at")
    if not captured:
        return float("inf")
    try:
        then = dt.datetime.fromisoformat(captured.replace("Z", "+00:00"))
    except ValueError:
        return float("inf")
    return (dt.datetime.now(dt.timezone.utc) - then).total_seconds()


def cache_is_usable(snapshot: dict | None, ttl: float) -> bool:
    if not snapshot:
        return False
    if not UPSTREAM_DIR.exists():
        return False
    if not (UPSTREAM_DIR / "docs").is_dir():
        return False
    if not SNAPSHOT_FILE.exists():
        return False
    return snapshot_age(snapshot) <= ttl


def load_robots(fetcher: Fetcher | None, allow_network: bool) -> RobotsPolicy | None:
    """robots.txt for the site we crawl over HTTP.  Cached alongside the snapshot."""
    if ROBOTS_FILE.exists():
        return RobotsPolicy(ROBOTS_FILE.read_text(encoding="utf-8"))
    if not allow_network or fetcher is None:
        return None
    data = fetcher.get(f"{SITE_ORIGIN}/robots.txt")
    ROBOTS_FILE.write_bytes(data)
    return RobotsPolicy(data.decode("utf-8", "replace"))


def git(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def refresh_upstream(fetcher: Fetcher) -> dict:
    """One git clone/fetch (~1 network operation) + one sitemap GET."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    if (UPSTREAM_DIR / ".git").is_dir():
        log(f"  git fetch {UPSTREAM_REPO}")
        git("-C", str(UPSTREAM_DIR), "fetch", "--depth", "1", "origin", UPSTREAM_BRANCH)
        git("-C", str(UPSTREAM_DIR), "reset", "--hard", "FETCH_HEAD")
    else:
        if UPSTREAM_DIR.exists():
            shutil.rmtree(UPSTREAM_DIR)
        log(f"  git clone --depth 1 {UPSTREAM_REPO}")
        git(
            "clone",
            "--depth",
            "1",
            "--single-branch",
            "--branch",
            UPSTREAM_BRANCH,
            "--quiet",
            UPSTREAM_REPO,
            str(UPSTREAM_DIR),
        )

    commit = git("-C", str(UPSTREAM_DIR), "rev-parse", "HEAD").stdout.strip()
    committed_at = git("-C", str(UPSTREAM_DIR), "log", "-1", "--format=%cI").stdout.strip()

    SITEMAP_FILE.write_bytes(fetcher.get(f"{SITE_ORIGIN}/sitemap.xml"))

    snapshot = {
        "upstream_repo": UPSTREAM_REPO,
        "upstream_repo_web": UPSTREAM_REPO_WEB,
        "upstream_branch": UPSTREAM_BRANCH,
        "upstream_commit": commit,
        "upstream_committed_at": committed_at,
        "sitemap_url": f"{SITE_ORIGIN}/sitemap.xml",
        "captured_at": utcnow(),
        "fetched_urls": [f"{UPSTREAM_REPO}", f"{SITE_ORIGIN}/sitemap.xml"],
        "http_requests": fetcher.request_count,
    }
    SNAPSHOT_FILE.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    return snapshot


def verify_single_page(fetcher: Fetcher, upstream_dir: Path) -> None:
    """Cross-check our per-page source against FMHY's own concatenated mirror."""
    if not SINGLE_PAGE_FILE.exists():
        SINGLE_PAGE_FILE.write_bytes(fetcher.get("https://api.fmhy.net/single-page"))
    single = SINGLE_PAGE_FILE.read_text(encoding="utf-8").lstrip("\ufeff")
    single = re.sub(r"^<!--.*?-->\s*", "", single, flags=re.S)

    list_src = (upstream_dir / "scripts" / "generate-single-page.js").read_text(encoding="utf-8")
    block = re.search(r"const files = \[(.*?)\]", list_src, re.S).group(1)
    files = re.findall(r"'([^']+)'", block)

    joined = "\n\n".join(
        (upstream_dir / "docs" / f).read_text(encoding="utf-8") for f in files
    )
    ok = INVISIBLE_CHARS_RE.sub("", joined).strip() == INVISIBLE_CHARS_RE.sub("", single).strip()
    log(f"  single-page cross-check: {'MATCH' if ok else 'DIFFERS'}")
    if not ok:
        log(
            "  note: the concatenated upstream files do not byte-match the API mirror; "
            "the pin may be mid-edit. Per-page sources are still authoritative."
        )


# --------------------------------------------------------------------------
# Taxonomy -- FMHY's own sidebar
# --------------------------------------------------------------------------


def _top_level_objects(src: str) -> list[str]:
    """Return the source spans of the top-level `{...}` elements of an array body."""
    spans: list[str] = []
    depth = 0
    start: int | None = None
    i = 0
    n = len(src)
    while i < n:
        c = src[i]
        if c in "'\"`":
            quote = c
            i += 1
            while i < n and src[i] != quote:
                if src[i] == "\\":
                    i += 1
                i += 1
        elif c in "[{":
            if c == "{" and depth == 0:
                start = i
            depth += 1
        elif c in "]}":
            depth -= 1
            if c == "}" and depth == 0 and start is not None:
                spans.append(src[start : i + 1])
                start = None
        i += 1
    return spans


def _field(span: str, name: str) -> str | None:
    m = re.search(rf"\b{name}\s*:\s*(['\"`])(.*?)\1", span, re.S)
    return m.group(2) if m else None


def _items_block(span: str) -> str | None:
    m = re.search(r"\bitems\s*:\s*\[", span)
    if not m:
        return None
    start = m.end() - 1
    depth = 0
    i = start
    while i < len(span):
        c = span[i]
        if c in "'\"`":
            quote = c
            i += 1
            while i < len(span) and span[i] != quote:
                if span[i] == "\\":
                    i += 1
                i += 1
        elif c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                return span[start + 1 : i]
        i += 1
    return None


def parse_taxonomy(shared_ts: str) -> list[dict]:
    """
    Recover FMHY's own top-level taxonomy from docs/.vitepress/shared.ts.

    Returns an ordered list of {class, label, paths}.  A sidebar *group* names a
    class; a *standalone* sidebar entry names a class after the first segment of
    its own path.  This is FMHY's structure, not ours.
    """
    m = re.search(r"export const sidebar[^=]*=\s*\[", shared_ts)
    if not m:
        return []
    body = shared_ts[m.end() :]
    depth = 1
    i = 0
    while i < len(body):
        c = body[i]
        if c in "'\"`":
            quote = c
            i += 1
            while i < len(body) and body[i] != quote:
                if body[i] == "\\":
                    i += 1
                i += 1
        elif c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                body = body[:i]
                break
        i += 1

    taxonomy: list[dict] = []
    for span in _top_level_objects(body):
        label = strip_html(_field(span, "text") or "").strip()
        link = _field(span, "link")
        items = _items_block(span)
        if items is not None:
            cls = slugify(label)
            paths: list[str] = []
            page_labels: dict[str, str] = {}
            for child in _top_level_objects(items):
                child_link = _field(child, "link")
                if child_link and child_link.startswith("/"):
                    paths.append(child_link)
                    child_label = display_title(strip_html(_field(child, "text") or ""))
                    if child_label:
                        page_labels[child_link] = child_label
            taxonomy.append(
                {
                    "class": cls,
                    "label": label,
                    "source": "sidebar-group",
                    "paths": paths,
                    "page_labels": page_labels,
                }
            )
        elif link and link.startswith("/"):
            cls = link.lstrip("/").split("#")[0].split("/")[0]
            taxonomy.append(
                {
                    "class": cls,
                    "label": label,
                    "source": "sidebar-item",
                    "paths": [link],
                    "page_labels": {link: display_title(label)},
                }
            )
    return taxonomy


def build_class_map(taxonomy: list[dict]) -> dict[str, tuple[str, str]]:
    """
    path (no leading slash) -> (source_class, class_label).

    Each sidebar link is registered together with its ancestor prefixes, so a
    class claimed by `/other/contributing` also covers the sibling `/other/*`
    pages that FMHY lists in its nav rather than its sidebar.
    """
    mapping: dict[str, tuple[str, str]] = {}

    def register(path: str, cls: str, label: str) -> None:
        parts = path.split("/")
        for i in range(len(parts), 0, -1):
            mapping.setdefault("/".join(parts[:i]), (cls, label))

    for entry in taxonomy:
        for link in entry["paths"]:
            path = link.lstrip("/").split("#")[0].rstrip("/")
            if not path:
                continue
            label = entry["label"]
            if entry["source"] == "sidebar-item" and "/" in path:
                # e.g. "Contribute" -> /other/contributing: the class really is
                # the `other` bucket, so label it after the bucket, not the leaf.
                label = path.split("/")[0].replace("-", " ").title()
            register(path, entry["class"], label)
    return mapping


def resolve_class(path: str, class_map: dict[str, tuple[str, str]]) -> tuple[str, str]:
    """
    A page inherits the class of its nearest indexed ancestor, so /posts/sept-2026
    lands in FMHY's `posts` entry and /other/FAQ in its `other` entry.  Pages with
    no indexed ancestor at all (FMHY never lists them in its sidebar) go to
    FALLBACK_CLASS.
    """
    parts = path.split("/") if path else []
    while parts:
        candidate = "/".join(parts)
        if candidate in class_map:
            return class_map[candidate]
        parts.pop()
    return (FALLBACK_CLASS, "Site")


# --------------------------------------------------------------------------
# Markdown parsing
# --------------------------------------------------------------------------

def _collect_nav_labels(src: str, out: dict[str, str]) -> None:
    for span in _top_level_objects(src):
        link = _field(span, "link")
        label = display_title(strip_html(_field(span, "text") or ""))
        if link and link.startswith("/"):
            path = link.lstrip("/").split("#")[0].rstrip("/")
            if path and label:
                out.setdefault(path, label)
        items = _items_block(span)
        if items is not None:
            _collect_nav_labels(items, out)


def parse_nav_labels(shared_ts: str) -> dict[str, str]:
    """
    FMHY's top nav lists pages the sidebar does not (FAQ, backups, selfhosting,
    wallpapers, feedback, startpage, search, changelog).  Used only as a source
    of page names; the taxonomy itself comes from the sidebar.
    """
    m = re.search(r"export const nav[^=]*=\s*\[", shared_ts)
    if not m:
        return {}
    body = shared_ts[m.end() :]
    depth = 1
    i = 0
    while i < len(body):
        c = body[i]
        if c in "'\"`":
            quote = c
            i += 1
            while i < len(body) and body[i] != quote:
                if body[i] == "\\":
                    i += 1
                i += 1
        elif c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                body = body[:i]
                break
        i += 1
    labels: dict[str, str] = {}
    _collect_nav_labels(body, labels)
    return labels


FRONTMATTER_RE = re.compile(r"\A\ufeff?---[ \t]*\r?\n(.*?)\r?\n---[ \t]*\r?\n", re.S)


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """
    VitePress frontmatter.  FMHY's `posts/*` pages carry their real page title
    here (`title:`), which is better than anything derivable from the body.
    Returns (fields, body-without-frontmatter).
    """
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    fields: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if line.lstrip().startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip().strip('"').strip("'")
    return fields, text[m.end() :]


HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
MD_LINK_RE = re.compile(r"\[([^\]]*)\]\(\s*<?([^)\s>]+)>?(?:\s+[\"'][^\"']*[\"'])?\s*\)")
AUTOLINK_RE = re.compile(r"<(https?://[^>\s]+)>")
BARE_URL_RE = re.compile(r"(?<![\w(<\]])(https?://[^\s<>\)\]\"'`]+)")
HTML_HREF_RE = re.compile(r"""href\s*=\s*["']([^"']+)["']""", re.I)


def extract_links(line: str) -> list[dict]:
    """Extract every link on a line, in source order, without double-counting."""
    found: list[tuple[int, int, str, str]] = []

    def add(pos: int, end: int, text: str, url: str) -> None:
        if not url or url.startswith("#"):
            return
        if url.lower().startswith(IGNORED_URL_PREFIXES):
            return
        found.append((pos, end, text, url))

    for m in MD_LINK_RE.finditer(line):
        add(m.start(), m.end(), m.group(1), m.group(2))
    for m in HTML_HREF_RE.finditer(line):
        add(m.start(), m.end(), "", m.group(1))
    for m in AUTOLINK_RE.finditer(line):
        add(m.start(), m.end(), m.group(1), m.group(1))

    def overlaps(pos: int, end: int) -> bool:
        return any(not (end <= s or pos >= e) for s, e, _, _ in found)

    for m in BARE_URL_RE.finditer(line):
        if not overlaps(m.start(), m.end()):
            add(m.start(), m.end(), m.group(1), m.group(1))

    found.sort(key=lambda r: r[0])
    out = []
    for _, _, text, url in found:
        out.append(
            {
                "link_text": INVISIBLE_CHARS_RE.sub("", text).strip(),
                "url": url.strip(),
                "raw": INVISIBLE_CHARS_RE.sub("", line).strip(),
            }
        )
    return out


def parse_page(markdown: str) -> list[dict]:
    """
    Split a source page into ordered blocks, keeping verbatim headings and
    verbatim link-bearing lines together with their heading breadcrumb.
    """
    blocks: list[dict] = []
    headings: dict[int, str] = {}

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or set(stripped) <= {"*", "-", "=", "_"} and len(stripped) <= 4:
            continue

        h = HEADING_RE.match(line)
        if h:
            level = len(h.group(1))
            text = INVISIBLE_CHARS_RE.sub("", h.group(2)).strip()
            headings = {k: v for k, v in headings.items() if k < level}
            headings[level] = text
            blocks.append(
                {
                    "kind": "heading",
                    "level": level,
                    "text": text,
                    "raw": line,
                    "breadcrumb": [headings[k] for k in sorted(headings)],
                }
            )
            continue

        # Raw markup (inline SVG, Vue component invocations, HTML blocks) is not
        # prose and not a link catalogue entry: only keep it if it carries a
        # markdown link.  Otherwise it is treated like prose.
        markup = stripped.startswith("<")
        if markup and not MD_LINK_RE.search(line):
            blocks.append(
                {
                    "kind": "markup",
                    "raw": line,
                    "breadcrumb": [headings[k] for k in sorted(headings)],
                }
            )
            continue

        links = extract_links(line)
        if links:
            blocks.append(
                {
                    "kind": "link-line",
                    "raw": INVISIBLE_CHARS_RE.sub("", line),
                    "links": links,
                    "breadcrumb": [headings[k] for k in sorted(headings)],
                }
            )
        else:
            blocks.append(
                {
                    "kind": "prose",
                    "raw": INVISIBLE_CHARS_RE.sub("", line),
                    "breadcrumb": [headings[k] for k in sorted(headings)],
                }
            )
    return blocks


# --------------------------------------------------------------------------
# Reference rendering
# --------------------------------------------------------------------------


def render_page(
    *,
    page_title: str,
    source_title: str | None,
    slug: str,
    source_class: str,
    source_url: str,
    upstream_path: str,
    upstream_blob: str,
    upstream_commit: str,
    captured_at: str,
    date: str,
    blocks: list[dict],
    link_count: int,
    with_prose: bool,
) -> str:
    out: list[str] = []
    out.append("---")
    out.append(f"page: {json.dumps(page_title, ensure_ascii=False)}")
    if source_title and source_title != page_title:
        out.append(f"source_title: {json.dumps(source_title, ensure_ascii=False)}")
    out.append(f"slug: {json.dumps(slug, ensure_ascii=False)}")
    out.append(f"source_class: {source_class}")
    out.append(f"source_url: {source_url}")
    out.append(f"upstream_path: {upstream_path}")
    out.append(f"upstream_blob: {upstream_blob}")
    out.append(f"upstream_commit: {upstream_commit}")
    out.append(f"captured_at: {captured_at}")
    out.append(f"link_count: {link_count}")
    out.append("---")
    out.append("")
    out.append("<!--")
    out.append(f"Structure, headings and link lines reproduced verbatim from FMHY ({source_url}),")
    out.append(f"captured {date}. FMHY Atlas is unaffiliated with and not endorsed by FMHY.")
    out.append("See ../../README.md for attribution and licence notes.")
    out.append("-->")
    out.append("")

    # One title line of our own, then the source's structure, headings and link
    # lines exactly as FMHY wrote them (FMHY's own first heading is a section
    # heading, not a page title, so it stays in place).
    out.append(f"# {page_title}")
    out.append("")

    for block in blocks:
        if block["kind"] == "heading":
            out.append(block["raw"])
            out.append("")
        elif block["kind"] == "link-line":
            out.append(block["raw"])
        elif with_prose:
            out.append(block["raw"])

    while out and out[-1] == "":
        out.pop()
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description="Build the FMHY Atlas reference repo.")
    ap.add_argument("--refresh", action="store_true", help="force a refetch of the upstream snapshot")
    ap.add_argument("--offline", action="store_true", help="never touch the network; require a cache")
    ap.add_argument("--ttl", type=float, default=DEFAULT_TTL_SECONDS, help="cache lifetime in seconds")
    ap.add_argument("--with-prose", action="store_true", help="also include non-link prose lines")
    ap.add_argument("--verify-single-page", action="store_true", help="cross-check the API mirror")
    args = ap.parse_args()

    log("FMHY Atlas builder")

    # ---- 1. snapshot ------------------------------------------------------
    log("[1/6] snapshot")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    snapshot = read_snapshot()
    cache_ok = cache_is_usable(snapshot, args.ttl) and not args.refresh

    fetcher = Fetcher(robots=None)
    if cache_ok:
        log("  cache hit -- no network requests")
    else:
        if args.offline:
            log("  cache miss and --offline set; aborting")
            return 2
        robots = load_robots(fetcher, allow_network=True)
        fetcher.robots = robots
        if robots:
            robots_txt = ROBOTS_FILE.read_text(encoding="utf-8")
            log("  robots.txt: " + " | ".join(l.strip() for l in robots_txt.splitlines() if l.strip()))
            if not robots.allowed(f"{SITE_ORIGIN}/sitemap.xml"):
                log("  robots.txt disallows /sitemap.xml -- aborting")
                return 3
        snapshot = refresh_upstream(fetcher)

    if args.verify_single_page and not args.offline:
        robots = fetcher.robots or RobotsPolicy(ROBOTS_FILE.read_text(encoding="utf-8"))
        fetcher.robots = None  # api.fmhy.net is a separate host; FMHY's own mirror
        verify_single_page(fetcher, UPSTREAM_DIR)

    assert snapshot is not None
    upstream_commit = snapshot["upstream_commit"]
    captured_at = snapshot["captured_at"]
    date = captured_at[:10]
    log(f"  upstream commit: {upstream_commit}")
    log(f"  captured_at:     {captured_at}")

    docs_dir = UPSTREAM_DIR / "docs"

    # ---- 2. taxonomy -----------------------------------------------------
    log("[2/6] taxonomy")
    shared_ts = (docs_dir / ".vitepress" / "shared.ts").read_text(encoding="utf-8")
    taxonomy = parse_taxonomy(shared_ts)
    class_map = build_class_map(taxonomy)
    log(f"  {len(taxonomy)} sidebar entries -> classes: "
        + ", ".join(e["class"] for e in taxonomy))
    if not taxonomy:
        log("  WARNING: could not parse the sidebar; every page falls back to "
            f"'{FALLBACK_CLASS}'")

    labels: dict[str, str] = {}
    exact_labels: dict[str, str] = parse_nav_labels(shared_ts)
    for entry in taxonomy:
        labels.setdefault(entry["class"], entry["label"])
        for link, label in entry.get("page_labels", {}).items():
            path = link.lstrip("/").split("#")[0].rstrip("/")
            if path:
                exact_labels[path] = label
    log(f"  {len(exact_labels)} page names from FMHY's sidebar + nav")

    # ---- 3. page list ----------------------------------------------------
    log("[3/6] page list")
    sitemap = SITEMAP_FILE.read_text(encoding="utf-8")
    sitemap_paths: list[str] = []
    for loc in re.findall(r"<loc>(.*?)</loc>", sitemap):
        path = urllib.parse.urlsplit(loc.strip()).path.strip("/")
        sitemap_paths.append(path)
    sitemap_paths = sorted(set(sitemap_paths))
    log(f"  sitemap.xml: {len(sitemap_paths)} URLs")

    source_files: dict[str, Path] = {}
    for md in sorted(docs_dir.rglob("*.md")):
        if ".vitepress" in md.parts:
            continue
        rel = md.relative_to(docs_dir).as_posix()
        path = rel[:-3]
        path = "" if path == "index" else path
        source_files[path] = md
    log(f"  upstream markdown pages: {len(source_files)}")

    missing = [p for p in sitemap_paths if p not in source_files]
    extra = [p for p in source_files if p not in set(sitemap_paths)]
    log(f"  in sitemap but no upstream markdown: {missing or 'none'}")
    log(f"  upstream markdown not in sitemap:    {extra or 'none'}")

    # ---- 4/5. references + manifest --------------------------------------
    log("[4/6] references/")
    if REFERENCES_DIR.exists():
        shutil.rmtree(REFERENCES_DIR)
    REFERENCES_DIR.mkdir(parents=True, exist_ok=True)

    records: list[dict] = []
    link_rows: list[dict] = []
    total_links = 0
    total_unique = 0

    def sort_key(path: str) -> tuple:
        return (0 if path in source_files else 1, path)

    for path in sorted(set(source_files) | set(sitemap_paths), key=sort_key):
        if path not in source_files:
            continue
        md_file = source_files[path]
        rel_from_docs = md_file.relative_to(docs_dir).as_posix()
        source_class, class_label = resolve_class(path, class_map)

        text = md_file.read_text(encoding="utf-8")
        frontmatter, text = parse_frontmatter(text)
        blocks = parse_page(text)

        file_name = Path(path).name if path else "index"
        slug = path or "index"
        source_url = f"{SITE_ORIGIN}/" + path

        source_title = None
        for block in blocks:
            if block["kind"] == "heading":
                source_title = display_title(block["text"]) or None
                break

        if not path:
            page_title = "FMHY Wiki Index"
        else:
            page_title = (
                display_title(frontmatter.get("title", ""))
                or display_title(exact_labels.get(path, ""))
                or source_title
                or display_title(Path(path).name.replace("-", " ").title())
            )
        page_title = page_title or slug

        links = [l for b in blocks if b["kind"] == "link-line" for l in b["links"]]
        link_count = len(links)
        total_links += link_count
        total_unique += len({l["url"] for l in links})

        out_dir = REFERENCES_DIR / source_class
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{file_name}.md"
        out_path.write_text(
            render_page(
                page_title=page_title,
                source_title=source_title,
                slug=slug,
                source_class=source_class,
                source_url=source_url,
                upstream_path=f"docs/{rel_from_docs}",
                upstream_blob=f"{UPSTREAM_REPO_WEB}/blob/{upstream_commit}/docs/{rel_from_docs}",
                upstream_commit=upstream_commit,
                captured_at=captured_at,
                date=date,
                blocks=blocks,
                link_count=link_count,
                with_prose=args.with_prose,
            ),
            encoding="utf-8",
        )

        for block in blocks:
            if block["kind"] != "link-line":
                continue
            breadcrumb = block["breadcrumb"]
            for link in block["links"]:
                link_rows.append(
                    {
                        "page": page_title,
                        "slug": slug,
                        "source_class": source_class,
                        "source_url": source_url,
                        "section": breadcrumb[0] if len(breadcrumb) > 0 else None,
                        "subsection": breadcrumb[1] if len(breadcrumb) > 1 else None,
                        "subsubsection": breadcrumb[2] if len(breadcrumb) > 2 else None,
                        "link_text": link["link_text"],
                        "url": link["url"],
                        "line": link["raw"],
                    }
                )

        records.append(
            {
                "page": page_title,
                "source_title": source_title,
                "slug": slug,
                "source_class": source_class,
                "class_label": class_label,
                "source_url": source_url,
                "captured_at": captured_at,
                "link_count": link_count,
                "unique_link_count": len({l["url"] for l in links}),
                "path": out_path.relative_to(REPO_ROOT).as_posix(),
                "upstream_path": f"docs/{rel_from_docs}",
                "upstream_blob": f"{UPSTREAM_REPO_WEB}/blob/{upstream_commit}/docs/{rel_from_docs}",
                "in_sitemap": path in sitemap_paths,
                "excluded_from_site": rel_from_docs.lower() in UPSTREAM_EXCLUDED_FROM_SITE,
            }
        )

    log(f"  wrote {len(records)} page files, {total_links} link occurrences")

    # ---- 6. manifest + link index ----------------------------------------
    log("[5/6] manifest.json + links.jsonl")
    by_class: dict[str, int] = {}
    for r in records:
        by_class[r["source_class"]] = by_class.get(r["source_class"], 0) + 1

    manifest = {
        "name": "fmhy-atlas",
        "description": (
            "Machine-readable reference of FMHY's public wiki. Unaffiliated with, "
            "and not endorsed by, FMHY."
        ),
        "generated_at": utcnow(),
        "builder": "build.py",
        "user_agent": USER_AGENT,
        "sources": {
            "upstream_repo": UPSTREAM_REPO_WEB,
            "upstream_commit": upstream_commit,
            "upstream_committed_at": snapshot.get("upstream_committed_at"),
            "sitemap_url": f"{SITE_ORIGIN}/sitemap.xml",
            "taxonomy_source": "docs/.vitepress/shared.ts (FMHY's own sidebar)",
            "captured_at": captured_at,
        },
        "licence": {
            "upstream_code": "Apache-2.0 (Copyright (c) taskylizard) - covers site code, not wiki content",
            "upstream_content": "No explicit content licence published by FMHY",
            "our_output": "Headings + link lines only; see README.md",
        },
        "counts": {
            "pages": len(records),
            "pages_in_sitemap": len(sitemap_paths),
            "pages_from_sitemap_indexed": sum(1 for r in records if r["in_sitemap"]),
            "link_occurrences": total_links,
            "unique_urls": total_unique,
            "by_class": by_class,
        },
        "taxonomy": [
            {
                "source_class": e["class"],
                "label": e["label"],
                "derived_from": e["source"],
                "paths": e["paths"],
            }
            for e in taxonomy
        ],
        "excluded_from_sitemap": [
            {"path": p, "reason": "no upstream markdown source (generated at build time)"}
            for p in missing
        ],
        "pages": records,
    }
    MANIFEST_FILE.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    with LINKS_FILE.open("w", encoding="utf-8") as fh:
        for row in link_rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    # ---- done ------------------------------------------------------------
    log("[6/6] done")
    log(f"  pages:            {len(records)}")
    log(f"  link occurrences: {total_links}")
    log(f"  unique URLs:      {total_unique}")
    for cls in sorted(by_class):
        log(f"    {cls:<18} {by_class[cls]:>3} pages")
    log(f"  http requests this run: {fetcher.request_count}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except urllib.error.URLError as exc:  # pragma: no cover - network failure path
        log(f"network error: {exc}")
        sys.exit(1)
