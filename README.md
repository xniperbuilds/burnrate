# burnrate

**Find out what is actually burning your coding-agent tokens — measured from your own sessions, not a marketing percentage.**

Every token-saving skill promises a number. `saves 65%`. `~31% lower bill`. Those numbers came from someone else's sessions, with someone else's files and habits. They are not yours, and you cannot check them.

So check yours. One command, no install, no API key, no network:

```bash
python burnrate.py --all
```

---

## The thing nobody measures

Here is a real 348-session corpus — 36,000 model turns, 8.8 billion tokens:

| | raw tokens | share | cost-weighted share |
|---|---:|---:|---:|
| **context re-sent every turn** (cache read) | 8,310,254,792 | **94.2%** | 49.6% |
| context written (cache write) | 446,493,285 | 5.1% | 33.3% |
| **output — what the agent writes** | 54,477,459 | **0.6%** | 16.3% |
| input (uncached) | 13,730,167 | 0.2% | 0.8% |

**Context: 99.2% of raw tokens, 82.9% cost-weighted. Output: 0.6% raw, 16.3% weighted.**

The median session re-sent **109x more context than it wrote**. Out of 348 sessions, **5** wrote more than they re-read.

Every skill that saves tokens by shortening replies, dropping articles, or talking like a caveman is optimizing the **0.6%**. Even weighted for the higher price of output tokens, it is going after the smallest of four line items — while adding its own instructions to the context that gets re-sent on every turn, forever.

That is why the savings never quite show up.

*(Both raw and cost-weighted shares are shown because they tell different stories. Raw is what fills your context window; weighted uses published billing ratios — cache write 1.25x, cache read 0.10x, output 5x input. Quoting only the flattering one is the problem, not the fix.)*

## Run it on your own numbers

```bash
git clone https://github.com/xniperbuilds/burnrate
cd burnrate/plugins/burnrate/skills/burnrate/scripts
python burnrate.py --days 30
```

Python 3.8+. Standard library only — no pip install, no Node, no shell installer, no `curl | bash`. Works the same on Windows, macOS and Linux.

It reads the transcripts already on your disk (`~/.claude/projects/**/*.jsonl`) and prints:

- your raw and cost-weighted token split
- which tools put the most volume into your context, and their average result size
- which files you read over and over
- which files are big enough to dominate a session on their own
- image and binary payloads, counted separately and honestly

```
  [HIGH] 94 file(s) read 5+ times
      Re-reading the same unchanged files cost roughly 2.4M tokens beyond the
      first read (approx). Worst: project-notes.md (107x).
      -> These are re-read because their content did not survive in context.

  [HIGH] Read produces 50% of everything fed back into context
      3.1K calls returned ~4.5M tokens total; average 1.4K tokens per call,
      largest single result ~16.8K tokens.
      -> Read with offset/limit instead of whole files.
```

## Prove your own savings

```bash
python burnrate.py --snapshot before
#  ... change something ...
python burnrate.py --compare before
```

`--compare` reports **per-turn averages**, so a busier week does not fake a regression:

```
                                             before        now    change
  cache write (new context)                    8.6K       5.9K    -31.7%
  cache read (context re-sent each turn)     213.3K     219.5K      2.9%
  output (what the agent writes)               1.4K       1.4K      1.3%

  cost-weighted per turn                      39.1K      36.4K     -6.9%

  This is your measured change. It is not a claim about anyone else's.
```

## Install as a skill

```
/plugin marketplace add xniperbuilds/burnrate
/plugin install burnrate@xniperbuilds
```

Installed, it does three things: measures before recommending, applies context discipline that targets the expensive 83–99% instead of the cheap 0.6%, and re-measures so the improvement is a fact. The full cut playbook — ranked by impact, with the cost of each cut stated — is in [`references/cuts.md`](plugins/burnrate/skills/burnrate/references/cuts.md).

## What it will not do

- **It will not make your agent talk strangely.** Telegraphic output degrades a small share of the bill while making results harder to review.
- **It will not quote you an average.** Only your measured numbers.
- **It will not hide its own cost.** The skill file loads into context when invoked. On short sessions that overhead can exceed what it saves — and `--compare` will show you that.
- **It will not trade correctness for tokens.** Concision applies to what is transmitted, never to reasoning, tests, or verbatim code and errors.

## Known limits

- Token totals come from the `usage` field and are exact. Tool-result volume is converted at ~4 chars/token and is labelled approximate everywhere it appears.
- Images and PDFs are billed by dimensions, not characters. They are counted separately and never converted into a token figure.
- Cost weighting uses published ratios between token classes, not per-model prices — so the weighted column is a share, not a currency amount.
- Subscription plans may weight usage differently from API pricing. Both raw and weighted shares are reported for that reason; neither is presented as a bill.
- Only local transcripts are visible. Work done on another machine or in the browser is not counted.
- The corpus above is one heavy user's 348 sessions. It is evidence, not a universal law — which is the entire point. Run it on yours.

## License

MIT
