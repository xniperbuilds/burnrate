# The cut playbook

Every cut below is ranked by measured impact and states what it costs you. Work top-down from the user's own `burnrate.py` findings — never apply a fix for a sink they do not have.

The ordering follows from one mechanic: **context is re-sent on every turn, output is written once.** A file read on turn 3 is paid again on turns 4, 5, 6 … until the session ends. That is why the ranking looks nothing like the usual "be concise" advice.

---

## Tier 1 — Big, permanent, no downside

Run `burnrate.py --startup` first — it tells you which of these three actually applies, with numbers.

### 0. Uninstall skills you do not use

Every installed skill's **description frontmatter** loads on every turn, whether or not the skill is ever invoked. The body does not — only the description. So the cost scales with how many skills are *installed*, not how many are *used*.

A machine with ~100 skills installed carries roughly 10–15K tokens of descriptions on every single turn. That is usually the largest attributable slice of startup context — bigger than `CLAUDE.md`.

- `--startup` lists the heaviest descriptions by name. Remove what you do not reach for.
- Long, keyword-stuffed `description:` fields cost the most. When writing your own skills, keep the description tight enough to trigger correctly and no longer.
- This cut costs nothing and breaks nothing.

**Cost:** none. **Payback:** every turn of every session, forever.

### 1. Shrink the always-loaded files

`CLAUDE.md`, `.claude/rules/*`, and the memory index load on **every turn of every session**. This is the only line item you pay for even when you do nothing.

- Target under 200 lines. Adherence drops on longer files anyway, so this cut buys accuracy as well as tokens.
- Delete anything the agent can derive from the codebase itself: directory layouts, dependency lists, architecture prose.
- Keep only what it would get *wrong* without being told: conventions that differ from defaults, pitfalls, rationale.
- Move procedures into skills. Skills load on demand; rules load always.
- Use path-scoped rules (`paths:` frontmatter) so per-area instructions load only when that area is touched.

**Cost:** an hour, once. **Payback:** every turn, forever.

### 2. Stop re-reading the same files

If `burnrate.py` reports a file read 5+ times, that file is being pulled in repeatedly because its content is not surviving in context — usually because the session is long, or the file is too big to hold.

- Read a region, not a file. Search first, then read around the hit.
- Never re-read a file you just edited.
- If a status/state file is genuinely needed every session, shrink it to an index and put detail in separate files that load on demand.

**Cost:** none. **Payback:** proportional to the repeat count.

### 3. Split oversized files

A 3,000-line source file read once occupies every subsequent turn of that session. Files that `burnrate.py` flags as >20K tokens are worth splitting on engineering grounds anyway.

**Cost:** a real refactor. **Payback:** large, and it improves the codebase.

---

## Tier 2 — Big, but requires a habit change

### 4. End sessions at unit boundaries

Cost grows with session length because every turn re-sends the whole prior conversation. A ten-hour session is not ten times a one-hour session — it is far worse.

- Finish a unit of work, write a short summary, start fresh.
- Do not keep one session open across unrelated tasks.
- After image-heavy or output-dump-heavy work, start a new session rather than dragging the payload forward.

**Cost:** you must write the hand-off summary. **Payback:** the largest single lever available after Tier 1.

### 5. Ask tools for less

- Line ranges over whole files; `head`/`tail` limits over full dumps.
- Narrow grep patterns over broad ones you then ignore.
- Quiet/short flags on build and test commands; full output only when something fails.
- Targeted test runs while iterating; full suite at the end.

**Cost:** slightly more thought per call. **Payback:** proportional to how noisy your tooling is.

### 6. Batch independent calls

Multiple independent tool calls in one turn cost one context re-send. The same calls spread over four turns cost four.

**Cost:** none. **Payback:** moderate, and it is faster.

---

## Tier 3 — Situational

### 7. Images and binaries

Billed by dimensions, not characters, and they stay in context for the rest of the session.

- Downscale screenshots before reading them.
- Prefer text-based inspection where it answers the question.
- Start a fresh session after image-heavy work.

### 8. Prune tool surface

Every connected MCP server and every loaded tool contributes schema text to context on every turn. Disconnect servers you are not using in this project.

### 9. Delegate bounded search to subagents

A subagent's exploration does not land in the parent's context — only its answer does. Good for broad bounded search; keep correctness-sensitive verification in the main thread.

**Caution:** a subagent has its own startup context. Fanning out many of them for small tasks costs more than it saves. Measure before making this a habit.

---

## Tier 4 — Real, but small. Do it; do not sell it as the fix.

### 10. Output discipline

- Lead with the answer. No preamble ("Sure! Here's…"), no postamble ("Let me know if…").
- Report deltas, not narration of the work.
- No restating the request back.

**Never** abbreviate: code, commands, file paths, error text, or test assertions. Truncating those causes a re-read next turn, which costs more than the words saved.

---

## Anti-patterns — cuts that cost more than they save

| Practice | Why it backfires |
|---|---|
| Telegraphic / "caveman" output | Attacks the smallest share of the bill; makes review harder and errors easier to miss |
| Skipping verification to save tokens | The bug surfaces later and costs a whole debugging session |
| Truncating error messages or code in replies | Guarantees a re-read next turn |
| Aggressive summarizing of decisions | The lost detail gets re-derived, at full price |
| Installing many always-on "efficiency" skills | Each one adds permanent context. Measure the net with `--compare` |
| Trusting a published "saves X%" figure | It was measured on someone else's sessions, with their file sizes and habits |

---

## Reporting the result

After applying cuts:

```bash
python scripts/burnrate.py --compare before
```

Give the user the per-turn delta as it comes out. If it is small, say it is small. If a cut made things worse, say that too and revert it. The measurement is the product — a number nobody can check is exactly what this skill was built to replace.
