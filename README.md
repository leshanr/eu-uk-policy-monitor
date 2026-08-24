# EU–UK policy monitor

A weekly legislative and regulatory monitoring pipeline covering two beats:
**EU–UK regulatory divergence** and **sanctions and economic security**.

It reads nine official EU and UK feeds, filters them against weighted keyword rules,
labels each item by what it actually is — adopted law, live legislation, consultation,
announcement — and produces a short digest to edit into a published brief.

Standard library Python only. No dependencies, no API keys, no paid tiers.

---

## Why it exists

Public affairs job specs ask for "experience of providing a legislative and policy
monitoring service". This is that service, run on your own account, in public. The
repo is the evidence; the published brief is the product.

---

## Setup (about 10 minutes)

1. Create a new **public** repository on GitHub — public matters, it is the thing
   you link to in applications.
2. Upload these files, keeping the folder structure. **`.github` is a hidden folder** —
   on Windows turn on View → Show → Hidden items, on macOS press **Cmd+Shift+.** in
   Finder, before selecting everything. If it still doesn't upload, create it in the
   browser: **Add file → Create new file**, name it `.github/workflows/weekly.yml`,
   paste the contents in, commit.
3. **Settings → Actions → General → Workflow permissions → Read and write permissions**,
   then Save. Skip this and the job runs but silently saves nothing.
4. **Actions** tab → *Weekly policy monitor* → **Run workflow**. This is the first
   time anything touches a live feed.
5. Open the run summary. It prints the digest and, at the bottom, a **source health**
   table showing which feeds worked.

After that it runs itself every Monday at 07:00 UTC and commits the new digest.

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

**`sources.json`** — nine feeds, every one confirmed live during setup. Tier 1
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

Nine sources feed both: EUR-Lex OJ L, the Council (where sanctions packages are
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
built on an automated monitoring pipeline of nine institutional sources — here is the
archive.*

---

## Scope

This monitors institutional publications: legislation, press releases, consultations
and bills. It is a policy monitoring tool, not a people-tracking one, and the source
list should stay that way.
