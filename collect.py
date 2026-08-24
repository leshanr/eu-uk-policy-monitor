#!/usr/bin/env python3
"""
Weekly EU/UK policy monitor.

Pulls a set of institutional RSS/Atom feeds, drops anything already seen,
scores what is left against the keyword themes in rules.json, and writes a
markdown digest you edit into a publishable brief.

Standard library only - no pip install, nothing to break in CI.

Usage:
    python3 collect.py                 # normal run, writes digests/YYYY-MM-DD.md
    python3 collect.py --check         # source health only, touches nothing
    python3 collect.py --days 14       # widen the window
    python3 collect.py --dry-run       # print the digest, do not save state
    python3 collect.py --no-state      # ignore the seen-items store entirely
"""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE_PATH = ROOT / "state" / "seen.json"
DIGEST_DIR = ROOT / "digests"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
TIMEOUT = 30
MAX_STATE = 4000  # keep the seen-store from growing without limit

ATOM = "{http://www.w3.org/2005/Atom}"

TYPE_LABELS = {
    "adopted": "ADOPTED",
    "in-progress": "IN PROGRESS",
    "consultation": "CONSULTATION",
    "announcement": "ANNOUNCEMENT",
}


# ----------------------------------------------------------------------------
# fetching
# ----------------------------------------------------------------------------

def fetch(url: str, attempts: int = 3) -> bytes:
    last = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9, */*;q=0.8",
                    "Accept-Encoding": "gzip",
                },
            )
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                raw = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                return raw
        except Exception as e:  # noqa: BLE001 - report, never crash the run
            last = e
    raise RuntimeError(f"{type(last).__name__}: {last}")


# ----------------------------------------------------------------------------
# parsing
# ----------------------------------------------------------------------------

def _text(el) -> str:
    if el is None:
        return ""
    return "".join(el.itertext()).strip()


def strip_html(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)
    s = (
        s.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
    )
    return re.sub(r"\s+", " ", s).strip()


def parse_date(s: str):
    if not s:
        return None
    s = s.strip()
    try:
        d = parsedate_to_datetime(s)
        if d is not None:
            return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)
    except Exception:  # noqa: BLE001
        pass
    iso = s.replace("Z", "+00:00")
    for candidate in (iso, iso[:19], iso[:10]):
        try:
            d = dt.datetime.fromisoformat(candidate)
            return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)
        except Exception:  # noqa: BLE001
            continue
    return None


def parse_feed(raw: bytes, source: dict) -> list[dict]:
    """Handle RSS 2.0 and Atom with one parser."""
    text = raw.decode("utf-8", errors="replace").lstrip()
    # Some endpoints serve an HTML page when the feed has moved.
    if text[:200].lower().lstrip().startswith("<!doctype html") or "<html" in text[:200].lower():
        raise RuntimeError("returned HTML, not a feed")
    root = ET.fromstring(text)

    items = []
    nodes = root.findall(".//item")
    kind = "rss"
    if not nodes:
        nodes = root.findall(f".//{ATOM}entry")
        kind = "atom"

    for n in nodes:
        if kind == "rss":
            title = _text(n.find("title"))
            link = _text(n.find("link"))
            summary = _text(n.find("description"))
            date = parse_date(
                _text(n.find("pubDate"))
                or _text(n.find("{http://purl.org/dc/elements/1.1/}date"))
                or _text(n.find(f"{ATOM}updated"))
                or _text(n.find("date"))
                or _text(n.find("published"))
            )
        else:
            title = _text(n.find(f"{ATOM}title"))
            link = ""
            for l in n.findall(f"{ATOM}link"):
                rel = l.get("rel", "alternate")
                if rel == "alternate" or not link:
                    link = l.get("href", "")
                    if rel == "alternate":
                        break
            summary = _text(n.find(f"{ATOM}summary")) or _text(n.find(f"{ATOM}content"))
            date = parse_date(_text(n.find(f"{ATOM}published")) or _text(n.find(f"{ATOM}updated")))

        title = strip_html(title)
        summary = strip_html(summary)

        # Some registers put a document code in <title> and the real subject in
        # the description. For those, swap them so scoring sees real words.
        if source.get("title_from_summary") and summary:
            code, title = title, summary
            summary = f"Document {code}" if code else ""

        if not title:
            continue
        items.append(
            {
                "title": title,
                "link": link.strip(),
                "summary": summary[:600],
                "date": date,
                "source": source["name"],
                "source_id": source["id"],
                "tier": source.get("tier", 2),
                "default_type": source.get("default_type"),
            }
        )
    return items


# ----------------------------------------------------------------------------
# scoring
# ----------------------------------------------------------------------------

def classify_type(item: dict, rules: dict, source: dict | None = None) -> str:
    """Label an item as adopted law, in-progress legislation, a consultation, or an announcement.

    A source may declare a default_type; explicit title patterns still win over it.
    """
    # Title only. A press release that merely mentions a Council Decision is not
    # itself the adopted act, and matching the summary made it look like one.
    hay = " " + item["title"].lower() + " "
    patterns = rules.get("type_patterns", {})
    for label in ("consultation", "adopted", "in-progress"):
        for p in patterns.get(label, []):
            if p in hay:
                return label
    if source and source.get("default_type"):
        return source["default_type"]
    if item.get("default_type"):
        return item["default_type"]
    return "announcement"


_KW_CACHE: dict[str, "re.Pattern[str]"] = {}


def _kw_pattern(kw: str) -> "re.Pattern[str]":
    """Whole-word matcher, so 'divergence' does not match 'neurodivergence'."""
    p = _KW_CACHE.get(kw)
    if p is None:
        body = re.escape(kw.lower())
        prefix = r"\b" if kw[:1].isalnum() else ""
        suffix = r"\b" if kw[-1:].isalnum() else ""
        p = re.compile(prefix + body + suffix)
        _KW_CACHE[kw] = p
    return p


def _theme_score(theme: dict, title: str, body: str) -> tuple[int, list[str]]:
    subtotal, hits = 0, []
    for kw, weight in theme["keywords"].items():
        pat = _kw_pattern(kw)
        if pat.search(title):
            subtotal += weight * 2
            hits.append(kw)
        elif pat.search(body):
            subtotal += weight
            hits.append(kw)
    return subtotal, hits


def score_item(item: dict, rules: dict) -> tuple[int, list[str], list[str]]:
    title = item["title"].lower()
    body = item["summary"].lower()

    for n in rules.get("noise", []):
        if n in title:
            return 0, [], []

    total = 0
    themes: list[str] = []
    hits: list[str] = []
    for theme in rules["themes"]:
        subtotal, theme_hits = _theme_score(theme, title, body)
        if subtotal:
            themes.append(theme["id"])
            total += subtotal
            hits.extend(theme_hits)

    if total:
        # A tier-1 institutional source gets a small edge over commentary.
        if item.get("tier") == 1:
            total += 1
        # Legal texts and live legislation outrank announcements about them.
        total += rules.get("type_bonus", {}).get(item.get("type", "announcement"), 0)
    return total, themes, sorted(set(hits))


def primary_theme(item: dict, rules: dict) -> str | None:
    """Assign each item to the single theme it scores highest in."""
    best, best_id = 0, None
    title = item["title"].lower()
    body = item["summary"].lower()
    for theme in rules["themes"]:
        s, _ = _theme_score(theme, title, body)
        if s > best:
            best, best_id = s, theme["id"]
    return best_id


# ----------------------------------------------------------------------------
# state
# ----------------------------------------------------------------------------

def item_key(item: dict) -> str:
    basis = item["link"] or item["title"]
    return hashlib.sha1(basis.encode("utf-8")).hexdigest()[:16]


def load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text())
        except Exception:  # noqa: BLE001
            pass
    return {"seen": []}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    state["seen"] = state["seen"][-MAX_STATE:]
    STATE_PATH.write_text(json.dumps(state, indent=1))


# ----------------------------------------------------------------------------
# output
# ----------------------------------------------------------------------------

def render(groups: dict, wider: list, health: list, rules: dict, window: int, now: dt.datetime) -> str:
    theme_names = {t["id"]: t["name"] for t in rules["themes"]}
    kept = sum(len(v) for v in groups.values()) + len(wider)

    out = []
    out.append(f"# Policy monitor — week to {now:%d %B %Y}")
    out.append("")
    out.append(
        f"*{kept} items from the last {window} days, drawn from "
        f"{sum(1 for h in health if h['ok'])} working sources. "
        "Raw output — edit before publishing.*"
    )
    out.append("")

    for theme in rules["themes"]:
        items = groups.get(theme["id"], [])
        if not items:
            continue
        out.append(f"## {theme_names[theme['id']]}")
        out.append("")
        for it in items:
            date = f"{it['date']:%d %b}" if it["date"] else "undated"
            link = it["link"] or ""
            title = f"[{it['title']}]({link})" if link else it["title"]
            tag = TYPE_LABELS.get(it.get("type", "announcement"), "ANNOUNCEMENT")
            out.append(f"- `{tag}` **{title}**  ")
            out.append(f"  {it['source']} · {date} · score {it['score']} · matched: {', '.join(it['hits'][:5])}")
            if it["summary"]:
                out.append(f"  > {it['summary'][:280]}")
            out.append("")
            out.append("  **So what:** ")
            out.append("")
        out.append("")

    if wider:
        out.append("## Wider catch")
        out.append("")
        out.append("*Below the threshold — scan, do not write up.*")
        out.append("")
        for it in wider:
            date = f"{it['date']:%d %b}" if it["date"] else "undated"
            link = it["link"] or ""
            title = f"[{it['title']}]({link})" if link else it["title"]
            tag = TYPE_LABELS.get(it.get("type", "announcement"), "ANNOUNCEMENT")
            out.append(f"- `{tag}` {title} — {it['source']}, {date}")
        out.append("")

    out.append("## Source health")
    out.append("")
    out.append("| Source | Status | Items |")
    out.append("|---|---|---|")
    for h in health:
        status = "ok" if h["ok"] else f"FAILED — {h['error']}"
        out.append(f"| {h['name']} | {status} | {h['count']} |")
    out.append("")
    return "\n".join(out)


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=None, help="lookback window in days")
    ap.add_argument("--check", action="store_true", help="test the feeds and exit")
    ap.add_argument("--dry-run", action="store_true", help="print to stdout, save nothing")
    ap.add_argument("--no-state", action="store_true", help="ignore the seen-items store")
    args = ap.parse_args()

    sources = json.loads((ROOT / "sources.json").read_text())["sources"]
    rules = json.loads((ROOT / "rules.json").read_text())
    window = args.days or rules.get("window_days", 8)
    now = dt.datetime.now(dt.timezone.utc)
    cutoff = now - dt.timedelta(days=window)

    all_items: list[dict] = []
    health: list[dict] = []

    for src in sources:
        try:
            raw = fetch(src["url"])
            items = parse_feed(raw, src)
            health.append({"name": src["name"], "ok": True, "count": len(items), "error": ""})
            all_items.extend(items)
            print(f"  ok   {src['id']}: {len(items)} items", file=sys.stderr)
        except Exception as e:  # noqa: BLE001
            health.append({"name": src["name"], "ok": False, "count": 0, "error": str(e)[:120]})
            print(f"  FAIL {src['id']}: {e}", file=sys.stderr)

    if args.check:
        working = sum(1 for h in health if h["ok"])
        print(f"\n{working}/{len(health)} sources returned a parseable feed.")
        for h in health:
            print(f"  {'ok  ' if h['ok'] else 'FAIL'}  {h['name']}  ({h['count']} items) {h['error']}")
        return 0 if working else 1

    state = {"seen": []} if args.no_state else load_state()
    seen = set(state.get("seen", []))

    fresh = []
    for it in all_items:
        if it["date"] and it["date"] < cutoff:
            continue
        key = item_key(it)
        if key in seen:
            continue
        it["key"] = key
        fresh.append(it)

    # dedupe within the run (the same story lands on several feeds)
    unique, run_seen = [], set()
    for it in sorted(fresh, key=lambda x: (x.get("tier", 2), x["title"])):
        norm = re.sub(r"[^a-z0-9]+", "", it["title"].lower())[:70]
        if norm in run_seen:
            continue
        run_seen.add(norm)
        unique.append(it)

    threshold = rules.get("score_threshold", 3)
    scored = []
    for it in unique:
        it["type"] = classify_type(it, rules)
        score, themes, hits = score_item(it, rules)
        if score <= 0:
            continue
        it.update({"score": score, "themes": themes, "hits": hits})
        scored.append(it)

    scored.sort(key=lambda x: -x["score"])
    groups: dict[str, list] = {}
    wider: list[dict] = []
    max_per = rules.get("max_per_theme", 5)
    max_total = rules.get("max_items_total", 8)
    filed = 0

    for it in scored:
        if it["score"] < threshold or filed >= max_total:
            wider.append(it)
            continue
        tid = primary_theme(it, rules)
        if tid is None:
            wider.append(it)
            continue
        bucket = groups.setdefault(tid, [])
        if len(bucket) < max_per:
            bucket.append(it)
            filed += 1
        else:
            wider.append(it)

    wider = wider[: rules.get("wider_catch_limit", 12)]
    digest = render(groups, wider, health, rules, window, now)

    if args.dry_run:
        print(digest)
        return 0

    DIGEST_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DIGEST_DIR / f"{now:%Y-%m-%d}.md"
    out_path.write_text(digest)
    print(f"\nwrote {out_path} ({sum(len(v) for v in groups.values())} filed, {len(wider)} wider)", file=sys.stderr)

    if not args.no_state:
        state["seen"] = list(state.get("seen", [])) + [it["key"] for it in unique]
        state["last_run"] = now.isoformat()
        save_state(state)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
