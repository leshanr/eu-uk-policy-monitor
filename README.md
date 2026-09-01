# EU–UK policy monitor

A weekly legislative and regulatory monitoring pipeline covering two beats:
**EU–UK regulatory divergence** and **sanctions and economic security**.

It reads twelve official EU and UK feeds, filters them against weighted keyword rules,
labels each item by what it actually is — adopted law, live legislation, consultation,
announcement — and produces a short digest to edit into a published brief.

Standard library Python only. No dependencies, no API keys, no paid tiers.

---


### Running it locally

```bash
python3 collect.py --check       # feed health only, writes nothing
python3 collect.py --dry-run     # print the digest without saving
python3 collect.py --days 14     # widen the window
python3 tests/test_offline.py    # verify the pipeline with sample feeds
```

---

## How it works

```
sources.json  →  fetch  →  parse (RSS + Atom)  →  window + dedupe  →  classify  →  score  →  digests/YYYY-MM-DD.md
                                                        ↑                              ↑
                                                  state/seen.json                  rules.json
```

**`sources.json`** — twelve feeds. `verified` means the endpoint parses; it says
nothing about whether the feed is still being updated, so read the **Age** column in
the digest's health table for that. Tier 1
(institutional primary sources) get a small scoring bonus over tier 2.

**`rules.json`** — the actual intelligence of the thing. Two themes of weighted
keywords; a title match counts double a body match. Items scoring below
`score_threshold` drop into a "wider catch" list you scan but do not write up. The
`noise` list kills diary items, media advisories and French-language Council items.

**`state/seen.json`** — every item ever surfaced, by hash. This is what stops the
digest repeating itself week to week.

**`digests/`** — one file per run, capped at eight filed items, each with a blank
**So what:** line. Those lines are the entire value you add.

### Item types

Every item is tagged by what stage it represents. The tag comes from title patterns
in `rules.json`, falling back to a source's `default_type`:

| Tag | Meaning |
|---|---|
| `ADOPTED` | Final legal text — an OJ act, a regulation in force, Royal Assent |
| `IN PROGRESS` | Proposals, committee stages, trilogue outcomes, bill readings |
| `CONSULTATION` | Calls for evidence and input, with their deadlines |
| `ANNOUNCEMENT` | Everything else — press releases, guidance, designations |

`ADOPTED` and `IN PROGRESS` items get a scoring bonus, so legal texts and live
legislation outrank announcements about them.

### A feed that parses is not a feed that works

The most useful thing this pipeline does is tell you when a source has quietly stopped
publishing. Two of the EU feeds parse cleanly, report items, and read as "ok" — while
having published nothing for four and eleven weeks respectively. A thin week may be a
thin week, or it may be a source list that has rotted.

The health table carries a **newest-item age** column and flags anything older than
`stale_after_days` (default 21) as **STALE**, in `--check` and in every digest. Check
that column before concluding it was quiet in Brussels.

### The brief

`briefs/TEMPLATE.md` is the structure of an issue with its word budget.
`briefs/000-worked-example.md` walks one real item from digest line to published
paragraph — the difference between reporting that something was published and saying
what changed for whom. `briefs/TUNING-LOG.md` records every miss and its fix; it is the
most credible file in the repo, because it is the one that admits what the filter cannot
see.

### Tests

`python3 tests/test_offline.py` — 22 checks, no network, run in CI before the collector.
It scores real headlines from the live feeds against the real `rules.json` and requires
each to clear the threshold, and requires genuinely off-beat items to score zero. Prune a
keyword and the test tells you what stopped being caught.

### Tuning

Tune `rules.json`, not `collect.py`. If a week returns too much, raise
`score_threshold` or cut low-value keywords — `russia`, `customs` and `single market`
are the broad ones. Too little, add keywords or widen `window_days`. Expect two or
three weeks of adjustment before the signal is right.

To add an EUR-Lex feed, find the `rssId` you want at
<https://eur-lex.europa.eu/predefined-rss.html> and add an entry pointing at
`https://eur-lex.europa.eu/EN/display-feed.rss?rssId=NNN`.

---

## The two beats

**EU–UK divergence and the reset.** Where the two rulebooks move apart and where the
reset negotiations pull them back: retained and assimilated law, the Windsor
Framework, SPS and veterinary alignment, conformity assessment, UKCA against CE
marking, data adequacy, the border target operating model. Genuinely
under-covered — most outlets report the politics of the reset, not the regulatory
mechanics of it.

**Sanctions and economic security.** Designations, general licences, export controls,
circumvention and shadow-fleet evasion, immobilised assets, investment screening.
Where the analysis can be better than anyone else's rather than merely present.

Twelve sources feed both: the Council register and press feeds (where sanctions packages are
actually adopted), the Commission, the European Parliament, OFSI, FCDO, DBT, UK
Parliament bills, and gov.uk.

---

## Turning the digest into a published brief

The digest is raw material. The edit is the job.

1. **Cut hard.** Eight items in, five out. A brief nobody finishes is worth nothing.
2. **Lead with divergence.** One item a week where EU and UK rules moved apart, what
   changed, and who now has two compliance regimes instead of one.
3. **Write the "so what" for a named reader.** Not "the Council adopted X" but "if you
   ship dual-use goods through a third country, X means Y from October".
4. **Prefer `ADOPTED` and `IN PROGRESS` items.** Anyone can rewrite a press release.
   Reading the legal text is the thing that isn't commodity.
5. **Link every claim to a primary source.** The digest already carries the links.
6. **Keep it to 600–800 words, fortnightly.** Fortnightly beats weekly if weekly means
   missing one.
7. **Be honest about uncertainty.** "This points toward X, though the text is ambiguous
   on Y" reads as analysis. Overclaiming reads as a student blog.

In applications: *I run a fortnightly EU–UK regulatory divergence and sanctions brief,
built on an automated monitoring pipeline of twelve institutional sources — here is the
archive.*

---

## Scope

This monitors institutional publications: legislation, press releases, consultations
and bills. It is a policy monitoring tool, not a people-tracking one, and the source
list should stay that way.
