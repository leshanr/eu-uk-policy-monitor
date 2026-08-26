# Worked example — one item, from digest line to published paragraph

Not an issue. A demonstration of the only step that matters, so the shape is on
record before issue 01 is written.

Every item below is real: these entries were live on the feeds on 26 August 2026.
The **So what** lines are written from the feed entries alone — before publishing any
of them, open the underlying text and check. That gap between "the feed said" and
"the document says" is the whole difference between this and an aggregator.

---

## Stage 1 — what the machine produces

This is exactly what lands in `digests/` on a Monday morning. Note the blank line.

```markdown
## EU–UK divergence and the reset

- **[Placing UKCA or CE marked products on the market in Great Britain](https://www.gov.uk/…)**
  gov.uk — Department for Business and Trade · 21 Aug · score 6 · matched: ukca
  > Guidance on conformity assessment and marking for goods placed on the GB market.

  **So what:**

## Sanctions and economic security

- **[OFSI General Licence INT/2025/7895596](https://www.gov.uk/…)**
  OFSI — financial sanctions (UK) · 12 Aug · score 7 · matched: general licence
  > Continuation of business — Lukoil Bulgaria entities.

  **So what:**
```

The machine has no view on either of these. It has told you they exist and that they
matched a keyword. That is all it will ever do.

---

## Stage 2 — the wrong version

The version that sounds like work and is worth nothing:

> **Commission and DBT publish updates on conformity assessment**
>
> The Department for Business and Trade has updated its guidance on placing UKCA or
> CE marked products on the market in Great Britain. Stakeholders should be aware of
> the changes and monitor developments closely.

Three failures, and they are always the same three. It reports that a thing was
published rather than what changed. It addresses "stakeholders", who do not exist.
And "monitor developments closely" is what you write when you have not read the
document.

---

## Stage 3 — the published version

> **UKCA and CE marking: the GB rules moved again**
>
> DBT updated its conformity assessment guidance on 21 August, covering how UKCA and
> CE marked goods may be placed on the Great Britain market.
>
> **So what:** if you sell the same product into GB and the EU, this is the page that
> decides whether one test certificate covers both or you pay for two. Read the
> effective dates before your next production run — the recognition arrangements here
> have been extended more than once, and each extension has had a different end date.
> The guidance is clear on what is accepted; it is less clear on what happens to
> certificates issued in the overlap.

> **UK licenses a Lukoil wind-down the EU has not mirrored**
>
> OFSI issued two general licences on 12 August covering continued business with
> Lukoil Bulgaria and Lukoil International entities, alongside a Russian Oil Exempt
> Projects licence on 6 August.
>
> **So what:** if you hold a contract with a Lukoil subsidiary, the UK has given you a
> defined route to keep performing it and EU law has not written the same one. Check
> the expiry date before you rely on it. A general licence *is* the divergence — and
> unlike a regulation, it lapses.

---

## What changed between stage 2 and stage 3

| | Wrong version | Published version |
|---|---|---|
| **Subject of the sentence** | the institution | the reader |
| **What it reports** | that something was published | what is now permitted or required |
| **Dates** | none | effective dates, expiry dates |
| **Uncertainty** | hidden behind "monitor closely" | named: what the text does not settle |
| **Could someone else have written it?** | yes, from the headline | no, only from the document |

---

## The recurring shapes

After a few issues most items turn out to be one of these. Recognising the shape is
most of the speed.

1. **A recognition arrangement with an end date.** The story is always the date.
2. **A general licence.** The story is what it permits and when it lapses.
3. **A UK bill that answers an EU act.** The story is the clauses that do not match.
4. **A duty or trade remedy.** The story is the supply chain that reroutes.
5. **A consultation closing.** The story is that the reader can still respond, and when.
