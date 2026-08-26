# Tuning log

Every time the filter misses something it should have caught, or catches something it
should not, it goes here with the fix. The misses are more interesting than the hits,
and after a few months this file becomes an issue of its own: *what a keyword filter
cannot see, and what that taught me*.

Format: date · what happened · why · what changed.

---

## 2026-08-26 — the one-item digest

**What prompted it:** the 25 August run fetched roughly 720 items across nine working
sources and filed **one**. The 24 August run filed three. A fortnightly brief needs
five good items; at that rate there is nothing to edit.

The health table could not tell me whether that was a genuinely quiet week, a threshold
set too high, or sources that had quietly stopped publishing. That inability was itself
the first thing to fix.

### Sources

Every endpoint was fetched and read by hand on 26 August.

| Finding | Fix |
|---|---|
| `ep-press` returned an empty body on both runs (`no element found: line 1, column 0`). When it does respond, its newest item was 12 June — eleven weeks stale. | Recorded in `sources.json`. Not solved: the committee feeds are the likely replacement. |
| `ec-presscorner` parses and reports 50 items, newest 31 July — four weeks stale. | Flagged. The API takes parameters; a per-DG endpoint may be fresher. |
| The OFSI feed carries general licences, guidance and FAQs. A new designation never appears in it. | Added `uk-sanctions-list` as a source. Endpoint unconfirmed — the first run's health table decides. |
| No source covered the cyber and digital file after DSIT was dropped. | Re-added `dsit`, confirmed live (newest item 24 Aug). |
| Nothing anywhere reported how old a feed's newest item was, so a dead source and a live one both read as "ok". | See **Code** below. |

### Keywords

Coverage went from 67 keywords to 185. Every addition is a term that appears in the
beat's own primary sources — the point was to stop missing real items, not to widen the
net for its own sake. Three named misses drove it:

| Item that got it wrong | Old score | Why | Fix |
|---|---|---|---|
| "Cyber Security and Resilience (Network and Information Systems) Bill" — UK Parliament, 26 Aug | **0** | Not one keyword matched. `cyber resilience` was in the rules, but the words are not adjacent in this title, and `nis2` is the EU's name for it, not Westminster's. This is the UK's answer to NIS2 — arguably the divergence story of the year on digital. | Added `cyber security` (4), `network and information systems` (5), `cyber resilience` (4), `nis2` (4). Now scores 21. |
| "Trade remedies notices: anti-dumping duty on welded tubes and pipes from Belarus and China" — DBT, 20 Aug | **below threshold** | The trade-defence vocabulary was thin. Trade defence is where economic security stops being rhetoric and becomes a duty rate somebody pays. | Added `trade remedies authority`, `countervailing`, `safeguard measure`, `definitive duty`; raised `anti-dumping` and `trade remedies` to 4. Now scores 23. |
| "Placing UKCA or CE marked products on the market in Great Britain" — DBT, 21 Aug | got in on `ukca` alone | `ce marking` never matches a real headline. They say "CE marked", "CE mark" or "CE-marked". | Added `ce marked` alongside `ce marking`. Deliberately **not** shortened to `ce mark`, which is a substring of "France market" and would fire on unrelated text. Now scores 19. |

Whole areas that had no coverage at all and now do: the Windsor Framework machinery
(`stormont brake`, `internal market scheme`, `dual regulatory`), the border model
(`common user charge`, `single trade window`, `safety and security declarations`),
conformity infrastructure (`designated standard`, `notified body`, `approved body`),
regulated sectors where divergence actually bites (`medical device`, `falsified
medicines`, `precision breeding`, `uk reach`), the carbon files (`ets linkage`,
`carbon border`, `cbam`), the reset's mobility strand (`youth experience scheme`,
`erasmus`), and on the sanctions side maritime enforcement (`dark fleet`, `port ban`,
`ship-to-ship`), illicit finance (`kleptocracy`, `unexplained wealth`, `virtual asset`)
and the frozen-assets debate (`immobilised assets`, `windfall profits`, `reparations
loan`).

**The lesson worth keeping:** keyword length is a trade-off in both directions. Too long
and it matches nothing real — `ce marking` missed every actual headline. Too short and
it matches the wrong thing — `ce mark` fires inside "France market", and `reach` fires on
"reach an agreement". Where a short stem is risky, list the two or three real surface
forms instead, and lean on the noise list for the rest.

### Code

| Bug | Effect | Fix |
|---|---|---|
| The health table reported that a feed parsed and how many items it held, never how old the newest of those items was. | Two badly stale EU sources have been passing as healthy for the life of the project. A thin digest was indistinguishable from a rotted source list. | Health now records newest-item date and age per source, flags anything older than `stale_after_days` (21) as **STALE**, and prints a warning above the table. Visible in `--check` and in every digest. |
| An item with no readable date skipped the window check entirely and always counted as fresh. | One static or badly-formatted feed could carry an entire run. | Undated now means out-of-window. The count is printed under the health table so a feed that goes fully undated is visible rather than silent. |

### Tests

Added `tests/test_offline.py` — 22 checks, no network, run in CI before the collector.
It scores seven real headlines from the live feeds against the **real** `rules.json` and
requires each to clear the threshold, and requires six genuinely off-beat items to score
zero. If someone prunes a keyword and the Cyber Bill stops being caught, that now fails
a test instead of quietly thinning a digest.

---

## Template for the next entry

```
## YYYY-MM-DD — [what prompted the look]

**Missed:** [headline] — [source], [date]. Scored [n].
**Why:** [which keyword should have caught it and did not]
**Fix:** [what changed in rules.json]
**Cost:** [what the brief would have said if it had caught it]
```
