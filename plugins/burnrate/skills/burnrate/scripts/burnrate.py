#!/usr/bin/env python3
"""burnrate - find out what is actually burning your coding-agent tokens.

Reads your own local session transcripts and reports measured numbers.
No API, no keys, no network, no dependencies. Python 3.8+, stdlib only.

Usage:
    python burnrate.py                    # last 30 days
    python burnrate.py --days 7
    python burnrate.py --all
    python burnrate.py --project myrepo   # filter by project dir name
    python burnrate.py --json             # machine-readable
    python burnrate.py --startup          # what loads before you type anything
    python burnrate.py --snapshot before  # save a baseline
    python burnrate.py --compare before   # measure what your changes did

Nothing here estimates or extrapolates. Every number printed was counted
from a file on this machine. Where a figure depends on an assumption
(price weighting), the assumption is printed next to it.
"""

import argparse
import collections
import glob
import json
import os
import re
import sys
import time

__version__ = "1.2.1"

# Relative billing weights vs base input tokens. Published Anthropic ratios:
# cache write = 1.25x input, cache read = 0.10x input, output = 5x input.
# These are RATIOS, not prices; they hold across the Claude model line even
# though absolute per-token prices differ per model.
WEIGHTS = {
    "input_tokens": 1.0,
    "cache_creation_input_tokens": 1.25,
    "cache_read_input_tokens": 0.10,
    "output_tokens": 5.0,
}

TOKEN_KEYS = list(WEIGHTS.keys())

LABEL = {
    "cache_read_input_tokens": "cache read (context re-sent each turn)",
    "cache_creation_input_tokens": "cache write (new context)",
    "output_tokens": "output (what the agent writes)",
    "input_tokens": "input (uncached)",
}

# Chars-per-token is a rough conversion used ONLY for tool-result volume,
# which the transcript does not tokenize for us. Flagged as approximate
# everywhere it is used.
CHARS_PER_TOKEN = 4

# Images are billed by dimensions, not by the size of their base64 payload,
# so the chars/token conversion is meaningless for them. They are counted
# separately and never folded into an approximate token figure.
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg", ".ico", ".pdf")


def is_image(path):
    return path.lower().endswith(IMAGE_EXT)


def transcript_root():
    env = os.environ.get("CLAUDE_CONFIG_DIR")
    if env:
        return os.path.join(os.path.expanduser(env), "projects")
    return os.path.join(os.path.expanduser("~"), ".claude", "projects")


def find_transcripts(root, days, project):
    if not os.path.isdir(root):
        return []
    files = glob.glob(os.path.join(root, "**", "*.jsonl"), recursive=True)
    if project:
        needle = project.lower()
        files = [f for f in files if needle in f.lower()]
    if days:
        cutoff = time.time() - days * 86400
        kept = []
        for f in files:
            try:
                if os.path.getmtime(f) >= cutoff:
                    kept.append(f)
            except OSError:
                pass
        files = kept
    return files


def human(n):
    n = int(n)
    for unit, div in (("B", 10**9), ("M", 10**6), ("K", 10**3)):
        if abs(n) >= div:
            return "%.1f%s" % (n / float(div), unit)
    return str(n)


class Report(object):
    def __init__(self):
        self.tokens = collections.Counter()
        self.sessions = 0
        self.files_scanned = 0
        self.turns = 0
        self.ratios = []
        self.tool_chars = collections.Counter()
        self.tool_calls = collections.Counter()
        self.tool_max = collections.Counter()
        self.read_counts = collections.Counter()
        self.read_chars = collections.Counter()
        self.image_reads = 0
        self.image_bytes = 0
        self.models = collections.Counter()
        self.first_turns = []       # startup context per session
        self.first_ts = None
        self.last_ts = None

    def note_ts(self, ts):
        if not ts:
            return
        if self.first_ts is None or ts < self.first_ts:
            self.first_ts = ts
        if self.last_ts is None or ts > self.last_ts:
            self.last_ts = ts


def scan(files):
    r = Report()
    for path in files:
        r.files_scanned += 1
        s = collections.Counter()
        id_to_tool = {}
        id_to_path = {}
        got_first = False
        try:
            fh = open(path, "r", encoding="utf-8", errors="replace")
        except (IOError, OSError):
            continue
        with fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    o = json.loads(line)
                except ValueError:
                    continue
                kind = o.get("type")
                msg = o.get("message")
                if not isinstance(msg, dict):
                    continue
                if kind == "assistant":
                    r.note_ts(o.get("timestamp"))
                    usage = msg.get("usage") or {}
                    if usage:
                        r.turns += 1
                        for k in TOKEN_KEYS:
                            s[k] += usage.get(k) or 0
                        if not got_first:
                            # First billed turn ~= the startup context: system prompt,
                            # tool schemas, CLAUDE.md, rules, memory index. Everything
                            # here is re-sent as cache_read on every later turn.
                            got_first = True
                            r.first_turns.append(
                                (usage.get("cache_creation_input_tokens") or 0)
                                + (usage.get("cache_read_input_tokens") or 0)
                                + (usage.get("input_tokens") or 0))
                    model = msg.get("model")
                    if model:
                        r.models[model] += 1
                    for b in msg.get("content") or []:
                        if isinstance(b, dict) and b.get("type") == "tool_use":
                            name = b.get("name") or "?"
                            r.tool_calls[name] += 1
                            id_to_tool[b.get("id")] = name
                            if name in ("Read", "NotebookRead"):
                                p = (b.get("input") or {}).get("file_path")
                                if p:
                                    id_to_path[b.get("id")] = p
                                    if not is_image(p):
                                        r.read_counts[p] += 1
                elif kind == "user":
                    content = msg.get("content")
                    if not isinstance(content, list):
                        continue
                    for b in content:
                        if not isinstance(b, dict) or b.get("type") != "tool_result":
                            continue
                        tid = b.get("tool_use_id")
                        name = id_to_tool.get(tid, "?")
                        body = b.get("content")
                        try:
                            if isinstance(body, str):
                                n = len(body)
                            elif body is None:
                                n = 0
                            else:
                                n = len(json.dumps(body))
                        except (TypeError, ValueError):
                            n = 0
                        p = id_to_path.get(tid)
                        if p and is_image(p):
                            # Billed by dimensions; a base64 char count would be a
                            # made-up token number, so it is kept out of the totals.
                            r.image_reads += 1
                            r.image_bytes += n
                            continue
                        r.tool_chars[name] += n
                        if n > r.tool_max[name]:
                            r.tool_max[name] = n
                        if p:
                            r.read_chars[p] += n
        if not any(s[k] for k in TOKEN_KEYS):
            continue
        r.sessions += 1
        r.tokens.update(s)
        if s["output_tokens"] > 0:
            r.ratios.append(s["cache_read_input_tokens"] / float(s["output_tokens"]))
    return r


# ---------------------------------------------------------------- startup scan

def _tok(path, cap_bytes=None):
    """Approximate tokens for a file. chars/4, same convention as everywhere else."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except (IOError, OSError):
        return 0, ""
    if cap_bytes and len(text.encode("utf-8", "replace")) > cap_bytes:
        text = text[: cap_bytes // 2]
    return len(text) // CHARS_PER_TOKEN, text


def _frontmatter(text):
    """Return (frontmatter_text, rest). Only the frontmatter of a skill/agent
    is loaded at startup - the body loads on demand. Counting whole files here
    is the mistake that makes other 'context budget' tools overstate."""
    if not text.startswith("---"):
        return "", text
    end = text.find("\n---", 3)
    if end == -1:
        return "", text
    return text[3:end], text[end + 4:]


def _claude_dir():
    env = os.environ.get("CLAUDE_CONFIG_DIR")
    return os.path.expanduser(env) if env else os.path.join(os.path.expanduser("~"), ".claude")


def skill_usage(root):
    """Count how often each skill was actually invoked.

    Deliberately scans the FULL transcript history, never the --days window:
    telling someone to delete a skill they used two months ago would be a
    worse error than saying nothing. Only explicit Skill tool calls are
    counted, so a skill reached another way will look unused - which is why
    this is reported as 'no invocation found', not 'never used'.
    """
    calls = collections.Counter()
    sessions = collections.Counter()
    scanned = 0
    for path in glob.glob(os.path.join(root, "**", "*.jsonl"), recursive=True):
        scanned += 1
        seen = set()
        try:
            fh = open(path, "r", encoding="utf-8", errors="replace")
        except (IOError, OSError):
            continue
        with fh:
            for line in fh:
                if '"Skill"' not in line:
                    continue                      # cheap prefilter
                try:
                    o = json.loads(line)
                except ValueError:
                    continue
                if o.get("type") != "assistant":
                    continue
                for b in (o.get("message") or {}).get("content") or []:
                    if not isinstance(b, dict) or b.get("type") != "tool_use":
                        continue
                    if b.get("name") != "Skill":
                        continue
                    nm = (b.get("input") or {}).get("skill")
                    if nm:
                        calls[nm] += 1
                        seen.add(nm)
        for nm in seen:
            sessions[nm] += 1
    return calls, sessions, scanned


def scan_startup(cwd=None):
    """Attribute the always-loaded context to the files that cause it."""
    cwd = cwd or os.getcwd()
    home = _claude_dir()
    comps = []          # (category, label, tokens, note)

    def add(cat, label, n, note=""):
        if n > 0:
            comps.append((cat, label, n, note))

    # --- instruction files ------------------------------------------------
    for label, path in (
        ("CLAUDE.md (user)", os.path.join(home, "CLAUDE.md")),
        ("CLAUDE.md (project)", os.path.join(cwd, "CLAUDE.md")),
        ("CLAUDE.md (.claude/)", os.path.join(cwd, ".claude", "CLAUDE.md")),
        ("CLAUDE.local.md", os.path.join(cwd, "CLAUDE.local.md")),
    ):
        if os.path.isfile(path):
            n, text = _tok(path)
            imports = re.findall(r"(?m)(?<![`\w])@([~./\w\\-]+\.\w+)", text)
            add("instructions", label, n,
                "%d @import(s)" % len(imports) if imports else "")
            for imp in imports[:20]:
                ip = os.path.expanduser(imp) if imp.startswith("~") else \
                    os.path.normpath(os.path.join(os.path.dirname(path), imp))
                if os.path.isfile(ip):
                    add("instructions", "  @%s" % os.path.basename(ip), _tok(ip)[0])

    # --- rules (always-loaded vs path-scoped) ----------------------------
    for base, scope in ((os.path.join(home, "rules"), "user"),
                        (os.path.join(cwd, ".claude", "rules"), "project")):
        if not os.path.isdir(base):
            continue
        always = scoped = 0
        n_always = n_scoped = 0
        for root_dir, _dirs, names in os.walk(base):
            for nm in names:
                if not nm.endswith(".md"):
                    continue
                n, text = _tok(os.path.join(root_dir, nm))
                fm, _ = _frontmatter(text)
                if "paths:" in fm:
                    scoped += n; n_scoped += 1
                else:
                    always += n; n_always += 1
        add("instructions", "rules/ %s (always)" % scope, always, "%d file(s)" % n_always)
        if scoped:
            comps.append(("deferred", "rules/ %s (path-scoped)" % scope, scoped,
                          "%d file(s), only when matched" % n_scoped))

    # --- memory index (capped by Claude Code at 200 lines / 25KB) --------
    mem_root = os.path.join(home, "projects")
    if os.path.isdir(mem_root):
        best = None
        for d in glob.glob(os.path.join(mem_root, "*", "memory", "MEMORY.md")):
            m = os.path.getmtime(d)
            if best is None or m > best[0]:
                best = (m, d)
        if best:
            add("instructions", "memory index (MEMORY.md)", _tok(best[1], 25600)[0],
                "capped at 200 lines / 25KB")

    # --- skills: ONLY the frontmatter loads at startup -------------------
    # A marketplace you have merely *browsed* leaves its whole catalogue on
    # disk. Those skills are not installed and never enter context, so
    # counting every SKILL.md under plugins/ overstates the bill badly.
    # Only paths named in installed_plugins.json are counted.
    skill_dirs = [os.path.join(home, "skills")]
    plug = os.path.join(home, "plugins")
    uncounted = 0
    if os.path.isdir(plug):
        installed_paths = []
        manifest = os.path.join(plug, "installed_plugins.json")
        if os.path.isfile(manifest):
            try:
                with open(manifest, "r", encoding="utf-8-sig", errors="replace") as fh:
                    for entries in (json.load(fh).get("plugins") or {}).values():
                        for e in entries or []:
                            p = e.get("installPath")
                            if p and os.path.isdir(p):
                                installed_paths.append(p)
            except (ValueError, IOError, OSError, AttributeError):
                installed_paths = None          # unreadable -> fall back
        else:
            installed_paths = None

        every = glob.glob(os.path.join(plug, "**", "skills"), recursive=True)
        if installed_paths is None:
            skill_dirs.extend(every)            # cannot tell; count them all
            scan_startup.plugin_filtered = False
        else:
            keep = [d for d in every
                    if any(os.path.normcase(os.path.abspath(d)).startswith(
                        os.path.normcase(os.path.abspath(p))) for p in installed_paths)]
            skill_dirs.extend(keep)
            uncounted = sum(len(glob.glob(os.path.join(d, "*", "SKILL.md")))
                            for d in every if d not in keep)
            scan_startup.plugin_filtered = True
    scan_startup.uncounted_plugin_skills = uncounted
    fm_tokens = body_tokens = count = 0
    heaviest = []
    seen = set()
    for sd in skill_dirs:
        for sk in glob.glob(os.path.join(sd, "*", "SKILL.md")):
            name = os.path.basename(os.path.dirname(sk))
            if name in seen:
                continue          # same skill via plugin + direct install
            seen.add(name)
            n, text = _tok(sk)
            fm, body = _frontmatter(text)
            count += 1
            t = len(fm) // CHARS_PER_TOKEN
            fm_tokens += t
            body_tokens += len(body) // CHARS_PER_TOKEN
            heaviest.append((t, name))
    heaviest.sort(reverse=True)
    add("descriptions", "skill descriptions", fm_tokens, "%d skill(s)" % count)
    scan_startup.heaviest_skills = heaviest[:6]
    scan_startup.skill_count = count
    scan_startup.all_skills = heaviest
    if body_tokens:
        comps.append(("deferred", "skill bodies", body_tokens,
                      "%d skill(s), load only when invoked" % count))

    # --- agents: frontmatter only ----------------------------------------
    ag_dir = os.path.join(home, "agents")
    if os.path.isdir(ag_dir):
        n_ag = t_ag = 0
        for ag in glob.glob(os.path.join(ag_dir, "*.md")):
            _, text = _tok(ag)
            fm, _ = _frontmatter(text)
            t_ag += len(fm) // CHARS_PER_TOKEN
            n_ag += 1
        add("descriptions", "agent descriptions", t_ag, "%d agent(s)" % n_ag)

    # --- MCP servers: schemas are real but not readable from disk --------
    servers = set()
    for cfg in (os.path.join(home, "settings.json"), os.path.join(cwd, ".mcp.json"),
                os.path.join(cwd, ".claude", "settings.json")):
        if not os.path.isfile(cfg):
            continue
        try:
            with open(cfg, "r", encoding="utf-8-sig", errors="replace") as fh:
                servers.update((json.load(fh).get("mcpServers") or {}).keys())
        except (ValueError, IOError, OSError, AttributeError):
            pass
    return comps, sorted(servers)


def print_startup(r, args):
    comps, servers = scan_startup(args.cwd)
    line = "=" * 66
    print(line)
    print(" burnrate %s  -  what loads before you type anything" % __version__)
    print(line)

    measured = None
    if r.first_turns:
        v = sorted(r.first_turns)
        measured = v[len(v) // 2]
        print("\n-- MEASURED (first billed turn of each session) ----------------")
        print("  median startup context   %9s tokens   across %d sessions"
              % ("{:,}".format(measured), len(v)))
        print("  p25 %s   p75 %s   max %s"
              % ("{:,}".format(v[len(v) // 4]), "{:,}".format(v[3 * len(v) // 4]),
                 "{:,}".format(v[-1])))
        print("  This is re-sent as cache_read on EVERY later turn of the session.")

    always = [c for c in comps if c[0] != "deferred"]
    deferred = [c for c in comps if c[0] == "deferred"]
    attributed = sum(c[2] for c in always)

    print("\n-- ATTRIBUTED (scanned from your config, approx) ---------------")
    for _cat, label, n, note in sorted(always, key=lambda x: -x[2]):
        print("  %-34s %9s  %s" % (label[:34], "{:,}".format(n), note))
    print("  %-34s %9s" % ("attributed total", "{:,}".format(attributed)))

    if measured:
        residual = measured - attributed
        print("\n  %-34s %9s  %s" % ("unattributed residual", "{:,}".format(residual),
                                     "system prompt + tool schemas" +
                                     (" + %d MCP server(s)" % len(servers) if servers else "")))
        if attributed:
            print("  %-34s %8.1f%%  of startup is yours to cut"
                  % ("your share", 100.0 * attributed / measured))

    if deferred:
        print("\n-- NOT loaded at startup (on demand only) ----------------------")
        for _cat, label, n, note in sorted(deferred, key=lambda x: -x[2]):
            print("  %-34s %9s  %s" % (label[:34], "{:,}".format(n), note))

    uncounted = getattr(scan_startup, "uncounted_plugin_skills", 0)
    if uncounted:
        print("\n  Ignored %d skill(s) from marketplaces you have browsed but not"
              % uncounted)
        print("  installed - they sit on disk and never enter context. Counting")
        print("  them, as a plain directory scan would, overstates startup badly.")
    elif getattr(scan_startup, "plugin_filtered", True) is False:
        print("\n  Note: installed_plugins.json could not be read, so every skill")
        print("  found under plugins/ was counted. Some may not actually load.")

    if servers:
        print("\n  MCP servers configured: %s" % ", ".join(servers))
        print("  Their tool schemas load every turn but are not readable from disk,")
        print("  so they sit inside the residual above rather than being guessed at.")

    print("\n-- FINDINGS ---------------------------------------------------")
    hits = 0
    for _cat, label, n, _note in sorted(always, key=lambda x: -x[2])[:3]:
        if n >= 1500:
            hits += 1
            print("\n  [%s] %s costs ~%s tokens on every turn"
                  % ("HIGH" if n >= 4000 else "MEDIUM", label, "{:,}".format(n)))
            print("      Over a 100-turn session that is ~%s tokens." % human(n * 100))
            if label == "skill descriptions":
                cnt = getattr(scan_startup, "skill_count", 0)
                allsk = getattr(scan_startup, "all_skills", [])
                print("      %d skill(s) installed. Every description loads every turn," % cnt)
                print("      whether or not you use the skill.")

                calls, sess, scanned = skill_usage(args.root or transcript_root())
                unused = [(t, nm) for t, nm in allsk if nm not in calls]
                wasted = sum(t for t, _ in unused)
                if calls:
                    print("\n      Across your ENTIRE history (%d transcripts, not the"
                          " --days window):" % scanned)
                    print("        %d installed  |  %d with a recorded invocation  |  %d without"
                          % (cnt, cnt - len(unused), len(unused)))
                    if unused:
                        print("\n      ~%s tokens per turn goes to skills with no recorded"
                              % "{:,}".format(wasted))
                        print("      invocation. Over a 100-turn session that is ~%s."
                              % human(wasted * 100))
                        print("      Heaviest of those:")
                        for t, nm in unused[:8]:
                            print("        %5s tok  %s" % ("{:,}".format(t), nm))
                        print("\n      -> Uninstalling these costs nothing and pays on every")
                        print("         turn of every future session.")
                        print("      -> Caveat: only explicit Skill tool calls are counted, so a")
                        print("         skill reached another way shows here too. Check the list")
                        print("         before deleting.")
                else:
                    print("      Heaviest:")
                    for t, nm in allsk[:6]:
                        print("        %5s tok  %s" % ("{:,}".format(t), nm))
                    print("      -> No Skill invocations found in your history, so usage could")
                    print("         not be measured. Uninstall what you know you do not use.")
    if measured and measured > 40000:
        hits += 1
        print("\n  [HIGH] Startup context is %s tokens before any work begins"
              % "{:,}".format(measured))
        print("      Every turn re-sends it. Shortening the files above is the only")
        print("      lever that pays on every turn of every future session.")
    if not hits:
        print("\n  Nothing oversized. Startup overhead is not your problem -")
        print("  run the main report to see where the tokens actually went.")

    print("\n" + line)
    print(" Attributed figures are approximate (chars/%d). The measured number" % CHARS_PER_TOKEN)
    print(" is exact. Only skill/agent FRONTMATTER is counted - bodies load on")
    print(" demand, so counting whole skill files would overstate this badly.")
    print(line)


def weighted(tokens):
    return dict((k, tokens[k] * WEIGHTS[k]) for k in TOKEN_KEYS)


def pct(part, whole):
    return 100.0 * part / whole if whole else 0.0


def build_findings(r):
    """Rank the actual sinks. Every finding carries the number it came from."""
    findings = []
    raw_total = sum(r.tokens[k] for k in TOKEN_KEYS)
    if not raw_total:
        return findings

    ctx = r.tokens["cache_read_input_tokens"] + r.tokens["cache_creation_input_tokens"]
    out = r.tokens["output_tokens"]
    w = weighted(r.tokens)
    w_total = sum(w.values())
    w_ctx = w["cache_read_input_tokens"] + w["cache_creation_input_tokens"]

    findings.append({
        "id": "where-the-bill-is",
        "severity": "info",
        "title": "Where your tokens actually go",
        "detail": (
            "Context is %.1f%% of raw tokens and %.1f%% cost-weighted. "
            "Output is %.1f%% raw / %.1f%% weighted."
            % (pct(ctx, raw_total), pct(w_ctx, w_total),
               pct(out, raw_total), pct(w["output_tokens"], w_total))),
        "action": (
            "Shortening the agent's replies targets the smaller share. "
            "Cut what is re-sent every turn instead."),
    })

    tool_total = sum(r.tool_chars.values())
    if tool_total:
        top = r.tool_chars.most_common(3)
        name, chars = top[0]
        calls = r.tool_calls[name] or 1
        findings.append({
            "id": "dominant-tool",
            "severity": "high" if pct(chars, tool_total) > 50 else "medium",
            "title": "%s produces %.0f%% of everything fed back into context" % (name, pct(chars, tool_total)),
            "detail": ("%s calls returned ~%s tokens total (approx, chars/%d); "
                       "average %s tokens per call, largest single result ~%s tokens."
                       % (human(calls), human(chars // CHARS_PER_TOKEN), CHARS_PER_TOKEN,
                          human(chars // calls // CHARS_PER_TOKEN),
                          human(r.tool_max[name] // CHARS_PER_TOKEN))),
            "action": ("Read with offset/limit instead of whole files; search first and "
                       "read only the matching region." if name in ("Read", "NotebookRead")
                       else "Narrow this tool's output before it enters context."),
        })

    repeats = [(p, c) for p, c in r.read_counts.items() if c >= 5]
    repeats.sort(key=lambda x: -x[1])
    if repeats:
        wasted = 0
        for p, c in repeats:
            per = r.read_chars[p] / float(c) if c else 0
            wasted += per * (c - 1)
        findings.append({
            "id": "repeat-reads",
            "severity": "high" if len(repeats) >= 10 else "medium",
            "title": "%d file(s) read 5+ times" % len(repeats),
            "detail": ("Re-reading the same unchanged files cost roughly %s tokens "
                       "beyond the first read (approx). Worst: %s (%dx)."
                       % (human(int(wasted // CHARS_PER_TOKEN)),
                          os.path.basename(repeats[0][0]), repeats[0][1])),
            "action": ("These are re-read because their content did not survive in context. "
                       "Shrink them, or stop pulling them in full."),
        })

    big = [(p, r.read_chars[p]) for p in r.read_chars]
    big.sort(key=lambda x: -x[1])
    heavy = [(p, c) for p, c in big[:5] if c // CHARS_PER_TOKEN > 20000]
    if heavy:
        findings.append({
            "id": "heavy-files",
            "severity": "medium",
            "title": "%d file(s) each pulled >20K tokens into context" % len(heavy),
            "detail": "; ".join("%s ~%s tok" % (os.path.basename(p), human(c // CHARS_PER_TOKEN))
                                for p, c in heavy),
            "action": "Split these, or read them by range. A file read once sits in every "
                      "subsequent turn's cache-read for the rest of the session.",
        })

    if r.image_reads >= 5:
        findings.append({
            "id": "image-reads",
            "severity": "medium",
            "title": "%d image/binary file(s) pulled into context" % r.image_reads,
            "detail": ("%.1f MB of base64 payload. Images are billed by dimensions, not "
                       "characters, so this tool does not convert them to a token count - "
                       "but each one stays in context for the rest of its session."
                       % (r.image_bytes / float(1024 * 1024))),
            "action": "Downscale before reading, and start a fresh session after image-heavy work.",
        })

    if r.ratios:
        rs = sorted(r.ratios)
        med = rs[len(rs) // 2]
        findings.append({
            "id": "ratio",
            "severity": "info",
            "title": "Median session re-sends %.0fx more context than it writes" % med,
            "detail": ("Measured across %d sessions. %d session(s) wrote more than they re-read."
                       % (len(rs), sum(1 for x in rs if x < 1))),
            "action": "Long sessions compound this. Ending a session clears the re-send base.",
        })

    return findings


def print_report(r, args):
    raw_total = sum(r.tokens[k] for k in TOKEN_KEYS)
    line = "=" * 66
    print(line)
    print(" burnrate %s  -  measured from your own transcripts" % __version__)
    print(line)

    if not raw_total:
        print("\nNo usage data found.")
        print("Looked in: %s" % transcript_root())
        if args.days and not args.all:
            print("Window: last %d days. Try --all." % args.days)
        return

    span = ""
    if r.first_ts and r.last_ts:
        span = "  %s -> %s" % (r.first_ts[:10], r.last_ts[:10])
    print("\n%d sessions, %d model turns, %d transcript files%s"
          % (r.sessions, r.turns, r.files_scanned, span))

    print("\n-- RAW TOKENS -------------------------------------------------")
    for k in sorted(TOKEN_KEYS, key=lambda x: -r.tokens[x]):
        print("  %-38s %9s  %5.1f%%" % (LABEL[k], human(r.tokens[k]), pct(r.tokens[k], raw_total)))
    print("  %-38s %9s" % ("TOTAL", human(raw_total)))

    w = weighted(r.tokens)
    w_total = sum(w.values())
    print("\n-- COST-WEIGHTED ----------------------------------------------")
    print("  (published ratios: cache write 1.25x, cache read 0.10x, output 5x input)")
    for k in sorted(TOKEN_KEYS, key=lambda x: -w[x]):
        print("  %-38s %9s  %5.1f%%" % (LABEL[k], human(w[k]), pct(w[k], w_total)))

    ctx_raw = r.tokens["cache_read_input_tokens"] + r.tokens["cache_creation_input_tokens"]
    w_ctx = w["cache_read_input_tokens"] + w["cache_creation_input_tokens"]
    print("\n  context  = %5.1f%% raw / %5.1f%% weighted" % (pct(ctx_raw, raw_total), pct(w_ctx, w_total)))
    print("  output   = %5.1f%% raw / %5.1f%% weighted"
          % (pct(r.tokens["output_tokens"], raw_total), pct(w["output_tokens"], w_total)))

    tool_total = sum(r.tool_chars.values())
    if tool_total:
        print("\n-- WHAT ENTERS CONTEXT (tool results, approx tokens) ----------")
        for name, chars in r.tool_chars.most_common(8):
            print("  %-34s %9s  %5.1f%%  calls=%d"
                  % (name[:34], human(chars // CHARS_PER_TOKEN), pct(chars, tool_total), r.tool_calls[name]))

    findings = build_findings(r)
    print("\n-- FINDINGS ---------------------------------------------------")
    rank = {"high": 0, "medium": 1, "info": 2}
    for f in sorted(findings, key=lambda x: rank.get(x["severity"], 3)):
        print("\n  [%s] %s" % (f["severity"].upper(), f["title"]))
        print("      %s" % f["detail"])
        print("      -> %s" % f["action"])

    print("\n" + line)
    print(" Numbers above were counted, not estimated. Values marked 'approx'")
    print(" convert characters to tokens at %d chars/token." % CHARS_PER_TOKEN)
    print(line)


def snapshot_dict(r):
    return {
        "version": __version__,
        "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "sessions": r.sessions,
        "turns": r.turns,
        "tokens": dict((k, r.tokens[k]) for k in TOKEN_KEYS),
        "tool_chars": dict(r.tool_chars),
        "tool_calls": dict(r.tool_calls),
        "image_reads": r.image_reads,
        "image_bytes": r.image_bytes,
    }


def snapshot_path(name):
    d = os.path.join(os.path.expanduser("~"), ".claude", "burnrate")
    if not os.path.isdir(d):
        os.makedirs(d)
    safe = "".join(c for c in name if c.isalnum() or c in "-_")
    return os.path.join(d, "%s.json" % (safe or "snapshot"))


def do_compare(r, name):
    path = snapshot_path(name)
    if not os.path.isfile(path):
        print("No snapshot named '%s'. Create one first:" % name)
        print("    python burnrate.py --snapshot %s" % name)
        return 1
    with open(path, "r", encoding="utf-8") as fh:
        old = json.load(fh)

    print("=" * 66)
    print(" burnrate compare  -  '%s' (saved %s) vs now" % (name, old.get("saved_at", "?")))
    print("=" * 66)

    old_turns = old.get("turns") or 0
    new_turns = r.turns or 0
    if not old_turns or not new_turns:
        print("\nNot enough turns on one side to compare.")
        return 1

    print("\nPer-turn averages (compares fairly across different session counts):")
    print("  %-38s %10s %10s %9s" % ("", "before", "now", "change"))
    old_tok = old.get("tokens", {})
    for k in TOKEN_KEYS:
        a = (old_tok.get(k) or 0) / float(old_turns)
        b = r.tokens[k] / float(new_turns)
        delta = pct(b - a, a) if a else 0.0
        print("  %-38s %10s %10s %8.1f%%" % (LABEL[k], human(a), human(b), delta))

    aw = sum((old_tok.get(k) or 0) * WEIGHTS[k] for k in TOKEN_KEYS) / float(old_turns)
    bw = sum(r.tokens[k] * WEIGHTS[k] for k in TOKEN_KEYS) / float(new_turns)
    print("\n  %-38s %10s %10s %8.1f%%" % ("cost-weighted per turn", human(aw), human(bw), pct(bw - aw, aw) if aw else 0))

    print("\n  before: %d turns / %d sessions      now: %d turns / %d sessions"
          % (old_turns, old.get("sessions", 0), new_turns, r.sessions))
    print("\n  This is your measured change. It is not a claim about anyone else's.")
    print("=" * 66)
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="burnrate",
        description="Find out what is actually burning your coding-agent tokens.")
    p.add_argument("--days", type=int, default=30, help="window in days (default 30)")
    p.add_argument("--all", action="store_true", help="scan every transcript")
    p.add_argument("--project", help="only transcripts whose path contains this string")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    p.add_argument("--snapshot", metavar="NAME", help="save current numbers as a baseline")
    p.add_argument("--compare", metavar="NAME", help="compare current numbers against a baseline")
    p.add_argument("--startup", action="store_true",
                   help="what loads before you type anything, and which files cause it")
    p.add_argument("--cwd", help="project directory to scan for --startup (default: current)")
    p.add_argument("--root", help="override transcript directory")
    p.add_argument("--version", action="version", version="burnrate " + __version__)
    args = p.parse_args(argv)

    root = args.root or transcript_root()
    days = None if args.all else args.days
    files = find_transcripts(root, days, args.project)

    if not files:
        print("No transcripts found in: %s" % root)
        print("If your agent stores sessions elsewhere, pass --root <dir>.")
        return 1

    r = scan(files)

    if args.startup:
        print_startup(r, args)
        return 0

    if args.compare:
        return do_compare(r, args.compare)

    if args.snapshot:
        path = snapshot_path(args.snapshot)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(snapshot_dict(r), fh, indent=2)
        print("Saved baseline '%s' (%d sessions, %d turns)" % (args.snapshot, r.sessions, r.turns))
        print("  %s" % path)
        print("\nNow change something, then run:")
        print("  python burnrate.py --compare %s" % args.snapshot)
        return 0

    if args.json:
        out = snapshot_dict(r)
        out["findings"] = build_findings(r)
        out["weighted"] = weighted(r.tokens)
        json.dump(out, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    print_report(r, args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
