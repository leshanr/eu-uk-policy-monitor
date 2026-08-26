#!/usr/bin/env python3
"""
Offline checks for the pipeline. No network, nothing written.

Two jobs:

  1. Parsing and plumbing — feed shapes that have broken this pipeline before,
     including RSS that carries its date in an Atom-namespaced <a10:updated> tag
     and feeds that parse perfectly while having published nothing for months.

  2. Keyword coverage — real headlines that were live on the feeds on
     26 August 2026, scored against the REAL rules.json. This is the regression
     net: if someone prunes a keyword and one of these stops clearing the
     threshold, that shows up here instead of as a silently thin digest.

Run:  python3 tests/test_offline.py
"""

import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import collect  # noqa: E402

RULES = json.loads((ROOT / "rules.json").read_text())
THRESHOLD = RULES["score_threshold"]
NOW = dt.datetime(2026, 8, 26, 12, 0, tzinfo=dt.timezone.utc)
FAILS = []


def check(label, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}{'' if ok else '  ' + detail}")
    if not ok:
        FAILS.append(label)


def item(title, summary="", tier=1, date=NOW):
    it = {"title": title, "summary": summary, "date": date, "link": "https://example.org/x",
          "source": "test", "source_id": "t", "tier": tier}
    it["type"] = collect.classify_type(it, RULES)
    return it


def scored(title, summary="", tier=1):
    return collect.score_item(item(title, summary, tier), RULES)[0]


# --------------------------------------------------------------- fixtures

# RSS 2.0 carrying its date in an Atom-namespaced tag, with no <pubDate>.
# UK Parliament bills and the Council press feed both look like this.
RSS_A10 = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:a10="http://www.w3.org/2005/Atom">
  <channel><title>UK Parliament — all bills</title>
    <item>
      <title>Cyber Security and Resilience (Network and Information Systems) Bill</title>
      <link>https://bills.parliament.uk/bills/9001</link>
      <description>A Bill to make provision about the security of network and information systems.</description>
      <a10:updated>2026-08-24T09:12:00Z</a10:updated>
    </item>
  </channel></rss>
"""

# Parses cleanly, last published twelve weeks ago. The shape that fooled the
# health table for the life of this project.
RSS_STALE = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"><channel><title>A feed that stopped</title>
  <item>
    <title>Modification of the existing maximum residue level for dodine in honey</title>
    <link>https://example.org/1</link><description>Scientific opinion.</description>
    <pubDate>Mon, 01 Jun 2026 09:38:07 +0200</pubDate>
  </item>
</channel></rss>
"""


def main():
    print("\nparsing")
    bills = collect.parse_feed(RSS_A10.encode(), {"name": "bills", "id": "b", "tier": 1})
    check("RSS with <a10:updated> and no <pubDate> yields dated items",
          all(i["date"] for i in bills), f"-> {[str(i['date']) for i in bills]}")
    check("the a10 timestamp is read correctly",
          bills[0]["date"] == dt.datetime(2026, 8, 24, 9, 12, tzinfo=dt.timezone.utc),
          f"-> {bills[0]['date']}")

    print("\nkeyword coverage — real headlines, live on the feeds 26 Aug 2026")
    must_catch = [
        ("Cyber Security and Resilience (Network and Information Systems) Bill",
         "UK Parliament, 26 Aug — the UK's answer to NIS2"),
        ("Placing UKCA or CE marked products on the market in Great Britain",
         "DBT, 21 Aug — conformity assessment"),
        ("Trade remedies notices: anti-dumping duty on welded tubes and pipes from Belarus and China",
         "DBT, 20 Aug — trade defence"),
        ("OFSI General Licence INT/2025/7895596",
         "OFSI, 12 Aug — Lukoil Bulgaria wind-down"),
        ("Position of the Council at first reading with a view to the adoption of a REGULATION "
         "establishing the Union Customs Code and the European Union Customs Authority",
         "Council register, 24 Aug — the one item the 25 Aug digest filed"),
        ("Russia's war of aggression against Ukraine: new EU sanctions target energy revenues, "
         "the military-industrial complex, propaganda and human rights violations",
         "Council press — a sanctions package"),
        ("Guidance: Cyber Resilience Pledge - list of signatories", "DSIT, 21 Aug"),
    ]
    for title, note in must_catch:
        sc = scored(title)
        check(f"caught ({sc:>3}): {note}", sc >= THRESHOLD,
              f"-> scored {sc}, threshold {THRESHOLD}")

    print("\nrelevance — things that must NOT reach the brief")
    must_skip = [
        ("Taiwan travel advice", "FCDO consular noise"),
        ("Weekly schedule of President António Costa", "diary item"),
        ("Households can save as plug-in solar panels come to market", "gov.uk, off-beat"),
        ("British Embassy Santiago presents recommendations to advance offshore wind "
         "development in Chile", "gov.uk, off-beat"),
        ("Official Statistics: UK trade in numbers", "statistics release"),
        ("Bluetongue virus restrictions updated", "DEFRA animal health"),
    ]
    for title, note in must_skip:
        sc = scored(title)
        check(f"skipped ({sc:>3}): {note}", sc < THRESHOLD, f"-> scored {sc}")

    print("\nstaleness")
    dead = collect.parse_feed(RSS_STALE.encode(), {"name": "dead", "id": "d", "tier": 2})
    age = (NOW - max(i["date"] for i in dead)).days
    check("a feed that parses but has stopped publishing is detected as stale",
          age > RULES.get("stale_after_days", 21), f"-> {age} days old")
    check("a live feed is not flagged stale",
          (NOW - bills[0]["date"]).days <= RULES.get("stale_after_days", 21))

    print("\nwindow")
    cutoff = NOW - dt.timedelta(days=RULES["window_days"])
    check("the stale item falls outside the window", max(i["date"] for i in dead) < cutoff)
    check("a recent item survives the window", bills[0]["date"] >= cutoff)

    print("\nrendering")
    health = [
        {"name": "gov.uk — DBT", "ok": True, "count": 20, "error": "",
         "newest": NOW, "age": 0, "undated": 0, "stale": False},
        {"name": "A feed that stopped", "ok": True, "count": 1, "error": "",
         "newest": max(i["date"] for i in dead), "age": age, "undated": 0, "stale": True},
        {"name": "European Parliament — press releases", "ok": False, "count": 0,
         "error": "no element found: line 1, column 0",
         "newest": None, "age": None, "undated": 0, "stale": False},
    ]
    filed = item("Placing UKCA or CE marked products on the market in Great Britain")
    sc, th, hi = collect.score_item(filed, RULES)
    filed.update({"score": sc, "themes": th, "hits": hi})
    md = collect.render({"eu-uk-divergence": [filed]}, [], health, RULES, 8, NOW, dropped=3)
    check("the digest warns when sources are stale", "sources are stale" in md)
    check("the health table carries an Age column", "| Age |" in md)
    check("a stale source is marked in the table", "**STALE**" in md)
    check("a failed source still appears", "FAILED" in md)
    check("undated items are reported", "no readable date" in md)
    check("every filed item gets a blank So what line", md.count("**So what:**") == 1)

    print()
    if FAILS:
        print(f"{len(FAILS)} check(s) failed:")
        for f in FAILS:
            print(f"  - {f}")
        print()
        return 1
    print("All checks passed.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
