#!/usr/bin/env python3
"""Step 2. Judge each company from its own LinkedIn text.

Claude Code does the judging. There is no Anthropic API key anywhere in this kit.

Two ways to run this step. Both read scripts/02_judge.md and brief.md and write work/judged.csv:

  A. Inside Claude Code: ask Claude to follow scripts/02_judge.md for work/companies.csv, 20 at a
     time, and write work/judged.csv. Then check its quotes:
         python3 scripts/02_judge.py --check work/judged.csv
  B. From the terminal, using your Claude Code login (headless `claude -p`):
         python3 scripts/02_judge.py

The check: a yes or no whose quote is not found word for word in the company's text becomes
"cannot tell". No quote, no verdict.

Also, for research answers that are not a clean yes or no (Tavily sentences, Serper results):
         python3 scripts/02_judge.py --review      -> work/research_review.csv
It follows scripts/03_review.md. Claude Code can do this step itself in the same way.

Other uses:  --input FILE.csv --output FILE.csv  judges any CSV with id, name, description columns.
"""
import argparse, json, re, subprocess, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import KIT, read_csv, write_csv

FIELDS = ["id", "name", "verdict", "reason", "quote", "confidence", "quote_in_text"]
SYSTEM = "You are a careful analyst. You follow the instructions exactly and reply with JSON only."


def squash(s):
    s = (s or "").lower()
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("—", "-").replace(" ", " ")
    return re.sub(r"\s+", " ", s).strip()


def quote_found(quote, text):
    """True when every piece of the quote (split at ... or the ellipsis character) is in the text."""
    q = squash(quote).strip(" \"'")
    if not q:
        return False
    t = squash(text)
    parts = [p.strip(" \"'.") for p in re.split(r"\.\.\.|…", q) if p.strip(" \"'.")]
    return bool(parts) and all(p in t for p in parts)


def apply_check(rows, companies):
    text = {c["id"]: c["description"] for c in companies}
    for r in rows:
        v = r["verdict"].strip().lower()
        r["verdict"] = v if v in ("yes", "no", "cannot tell") else "cannot tell"
        if r["verdict"] in ("yes", "no"):
            ok = quote_found(r["quote"], text.get(r["id"], ""))
            r["quote_in_text"] = "yes" if ok else "no"
            if not ok:
                r["reason"] = f"[quote not found in the text, so verdict was {r['verdict']}] " + r["reason"]
                r["verdict"], r["confidence"] = "cannot tell", "low"
        else:
            r["quote_in_text"] = ""
    return rows


def ask_claude(prompt, model):
    with tempfile.TemporaryDirectory() as tmp:  # run from an empty folder so no project files load
        try:
            p = subprocess.run(
                ["claude", "-p", "--model", model, "--tools", "", "--strict-mcp-config",
                 "--system-prompt", SYSTEM, "--output-format", "text"],
                input=prompt, capture_output=True, text=True, cwd=tmp, timeout=900)
        except FileNotFoundError:
            sys.exit("The `claude` command was not found. Install Claude Code and log in, "
                     "or ask Claude Code to do this step itself (see README).")
    if p.returncode != 0:
        sys.exit("claude -p failed: " + (p.stderr or p.stdout)[:500])
    return p.stdout


def parse_json_array(text):
    a, b = text.find("["), text.rfind("]")
    if a < 0 or b < a:
        raise ValueError("no JSON array in the answer")
    return json.loads(text[a:b + 1])


REVIEW_FIELDS = ["id", "tool", "verdict", "reason"]


def review_items(d):
    """Research answers that are not a clean yes or no, as text for Claude to read."""
    items = []
    for tool in ("parallel", "exa", "tavily", "serper"):
        p = d / f"research_{tool}.json"
        if not p.is_file():
            continue
        for r in json.loads(p.read_text()):
            if r.get("answer") in ("yes", "no") or r.get("answer_text", "").startswith("[error]"):
                continue
            text = r.get("answer_text", "")
            for h in r.get("results", []):
                text += f" || {h.get('title', '')} ({h.get('link', '')}): {h.get('snippet', '')}"
            items.append({"id": r["id"], "tool": tool, "question": r.get("question") or r.get("query", ""),
                          "text": text.strip()})
    return items


def run_review(a, d):
    items = review_items(d)
    if not items:
        print("Nothing to review: every research answer was already a clean yes or no.")
        return
    template = (KIT / "scripts" / "03_review.md").read_text()
    out = []
    for i in range(0, len(items), a.batch):
        chunk = items[i:i + a.batch]
        prompt = template.replace("{{ITEMS}}", json.dumps(chunk, indent=1))
        print(f"Claude: reading items {i + 1}-{i + len(chunk)} of {len(items)} ...", flush=True)
        for attempt in (1, 2):
            try:
                got = parse_json_array(ask_claude(prompt, a.model))
                break
            except (ValueError, json.JSONDecodeError) as e:
                if attempt == 2:
                    sys.exit(f"Claude's answer was not valid JSON twice: {e}")
        have = {(str(g.get("id")), str(g.get("tool"))): g for g in got}
        for it in chunk:
            g = have.get((it["id"], it["tool"]), {})
            v = str(g.get("verdict", "cannot tell")).strip().lower()
            out.append({"id": it["id"], "tool": it["tool"], "verdict": v if v in ("yes", "no", "cannot tell") else "cannot tell",
                        "reason": str(g.get("reason", "[no answer returned]"))})
    write_csv(d / "research_review.csv", out, REVIEW_FIELDS)
    print(f"Wrote {d / 'research_review.csv'}: {len(out)} items read.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="work")
    ap.add_argument("--input", default="companies.csv")
    ap.add_argument("--output", default="judged.csv")
    ap.add_argument("--brief", default=str(KIT / "brief.md"))
    ap.add_argument("--batch", type=int, default=20)
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--review", action="store_true", help="read research answers that are not a clean yes or no")
    ap.add_argument("--check", metavar="JUDGED_CSV", help="only check the quotes in a CSV Claude already wrote")
    a = ap.parse_args()
    d = Path(a.dir)
    if a.review:
        return run_review(a, d)
    companies = read_csv(d / a.input)

    if a.check:
        path = Path(a.check)
        rows = read_csv(path)
        rows = apply_check(rows, companies)
        write_csv(path, rows, FIELDS)
        bad = [r for r in rows if "[quote not found" in r["reason"]]
        print(f"Checked {len(rows)} rows in {path}. {len(bad)} downgraded to 'cannot tell' (quote not in text).")
        return

    template = (KIT / "scripts" / "02_judge.md").read_text()
    brief = Path(a.brief).read_text()
    out = []
    for i in range(0, len(companies), a.batch):
        chunk = companies[i:i + a.batch]
        payload = json.dumps([{"id": c["id"], "name": c["name"], "text": c["description"]} for c in chunk], indent=1)
        prompt = template.replace("{{BRIEF}}", brief).replace("{{COMPANIES}}", payload)
        print(f"Claude: companies {i + 1}-{i + len(chunk)} of {len(companies)} ...", flush=True)
        for attempt in (1, 2):
            try:
                got = parse_json_array(ask_claude(prompt, a.model))
                break
            except (ValueError, json.JSONDecodeError) as e:
                if attempt == 2:
                    sys.exit(f"Claude's answer was not valid JSON twice: {e}")
        names = {c["id"]: c["name"] for c in chunk}
        seen = set()
        for g in got:
            gid = str(g.get("id"))
            if gid in names:
                seen.add(gid)
                out.append({"id": gid, "name": names[gid], "verdict": str(g.get("verdict", "")),
                            "reason": str(g.get("reason", "")), "quote": str(g.get("quote", "")),
                            "confidence": str(g.get("confidence", ""))})
        for gid in names:
            if gid not in seen:
                out.append({"id": gid, "name": names[gid], "verdict": "cannot tell",
                            "reason": "[no answer returned for this company]", "quote": "", "confidence": "low"})
    out.sort(key=lambda r: int(r["id"]) if r["id"].isdigit() else r["id"])
    out = apply_check(out, companies)
    write_csv(d / a.output, out, FIELDS)
    n = {k: sum(1 for r in out if r["verdict"] == k) for k in ("yes", "no", "cannot tell")}
    print(f"Wrote {d / a.output}: {n['yes']} yes, {n['no']} no, {n['cannot tell']} cannot tell.")


if __name__ == "__main__":
    main()
