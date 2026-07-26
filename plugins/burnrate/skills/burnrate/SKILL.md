---
name: burnrate
description: Find out what is actually burning your coding-agent tokens, then cut it — measured from your own session transcripts, never a claimed percentage. Use whenever the user says they are hitting usage limits, burning tokens too fast, "limit khatam ho gaya", "why is this so expensive", "reduce token usage", "my context fills up too fast", "session limit", "running out of quota", asks to make an agent cheaper or more efficient, wants to know where their tokens went, or is evaluating a token-saving tool or skill. Also use before adopting any "saves X% tokens" claim — this skill measures the real split first.
---

# burnrate

Most token-saving advice optimizes the wrong thing.

The agent's *output* — the part everyone tries to shorten — is a small minority of what you are billed for. The bill is dominated by **context: the conversation re-sent on every single turn**. Shortening replies attacks the visible number, not the expensive one.

This skill measures the actual split on **this user's machine**, names the specific files and tools driving it, cuts those, and then measures again so the improvement is a fact rather than a claim.

## The prime rule

> **Never state a saving you did not measure.**

No "~30% cheaper". No "cuts 65% of tokens". If you have not run the before/after on this user's own transcripts, you do not have a number, and you say so. Every competing tool in this space leads with an average from someone else's sessions. That average is not the user's, and pretending otherwise is the failure this skill exists to correct.

Corollary: never trade correctness, test coverage, or verbatim accuracy of code/commands/errors for tokens. A cheaper wrong answer costs more than an expensive right one — you pay for it again in the next turn.

---

## Step 1 — Measure first, always

Run the analyzer before recommending anything:

```bash
python scripts/burnrate.py --days 30
```

Zero dependencies, stdlib Python 3.8+, no network, no keys. It reads `~/.claude/projects/**/*.jsonl` (override with `--root`). Useful flags: `--all`, `--days N`, `--project <name>`, `--json`.

It reports four things:

1. **Raw token split** across cache-read / cache-write / output / input.
2. **Cost-weighted split**, using published billing ratios (cache write 1.25x, cache read 0.10x, output 5x input). Report *both* — raw shows what fills the context window, weighted shows what costs money. They tell different stories and quoting only the flattering one is the exact dishonesty this skill rejects.
3. **What enters context** — which tools return the most volume, and how big their average result is.
4. **Ranked findings** — repeated reads, oversized files, image payloads, session-length effects.

Report the user's real numbers back to them before proposing a single change.

## Step 2 — Cut the top sink, not the famous one

Read `references/cuts.md`. It ranks every available cut by measured impact and states what each one costs you. Work strictly top-down from the user's own findings — a fix for a sink they do not have is wasted effort and wasted tokens.

The usual order of impact:

1. Files pulled into context in full, repeatedly
2. Oversized always-loaded instruction files (`CLAUDE.md`, memory index, rules)
3. Tool results that arrive far larger than needed
4. Session length — every turn re-sends everything before it
5. Images and binaries
6. Output verbosity — last, and smallest

## Step 3 — Prove it

```bash
python scripts/burnrate.py --snapshot before
# ... apply the cuts ...
python scripts/burnrate.py --compare before
```

`--compare` reports **per-turn averages**, so a week with more sessions does not masquerade as a regression. Give the user that delta verbatim, including when it is small or negative. A cut that did nothing is a finding worth reporting — it stops them from paying for it in effort forever.

---

## Always-on context discipline

These are the habits that produce the numbers above. Apply them by default in any session where this skill is active. They target context, which the measurements show is the expensive half; none of them shorten reasoning or degrade answers.

**Reading files**
- Search before reading. Locate the region, then read that region — `offset`/`limit`, not the whole file.
- Never re-read a file you just wrote or edited. You already know its contents.
- Never re-read an unchanged file to "check". If it mattered, it is still in context.
- Read one authoritative file rather than three overlapping ones.

**Tool results**
- Ask tools for less: line ranges, head/tail limits, specific fields, `--quiet` variants.
- Filter at the source. A grep with a narrow pattern beats a broad one you then ignore.
- Batch independent calls in one turn — fewer turns means fewer full-context re-sends.

**Session shape**
- Every turn re-sends everything before it, so cost grows with session length, not just with what you do next. Long exploratory sessions are the single most expensive habit.
- Finish a unit of work, then start fresh. Carry forward a short written summary instead of the whole history.
- After image-heavy or dump-heavy work, start a new session rather than dragging the payload along.

**Always-loaded files**
- `CLAUDE.md`, rules, and the memory index load on every single turn of every session. A 400-line `CLAUDE.md` is not paid once — it is paid per turn, forever.
- This is the highest-leverage file in the entire setup. Treat every line in it as a recurring charge.

**Output** *(smallest lever — do this, but do not sell it as the fix)*
- Lead with the answer; no preamble, no postamble, no restating the request.
- Report the delta, not a narration of the work.
- Never abbreviate code, commands, file paths, or error text.

---

## What this skill will not do

Stated plainly, because the alternatives in this category do these things:

- **It will not make the agent talk strangely.** Telegraphic or "caveman" output degrades a small share of the bill while making results harder to use and reviews harder to trust.
- **It will not claim an average.** Only this user's measured numbers.
- **It will not hide its own cost.** This file loads into context when the skill is invoked. On short sessions that overhead can exceed what it saves, and `--compare` will show that honestly.
- **It will not cut reasoning, tests, or verification.** Concision applies to what is transmitted, never to what is thought or checked.

## Known limits

- Tool-result volume is converted at ~4 chars/token. That is an approximation, labelled as one everywhere it appears. Token totals from the `usage` field are exact.
- Images and PDFs are billed by dimensions, not characters, so the tool counts them separately and refuses to convert them to a token number.
- Cost weighting uses published ratios between token classes, not per-model prices, so weighted output is a share, not a currency amount.
- Subscription plans (Pro/Max) may weight usage differently from API pricing. Raw and weighted shares are both reported for that reason; neither is presented as a bill.
- It reads only local transcripts. Work done on other machines or in the browser is not visible to it.
