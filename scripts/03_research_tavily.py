#!/usr/bin/env python3
"""Step 3 (option B). Ask Tavily the sharp question about each unsure company.

Tavily search returns a short written answer plus the pages it came from. 1 credit per company
with search_depth "basic".

Reads  : work/companies.csv, work/judged.csv, brief.md (the RESEARCH_QUESTION line)
Writes : work/research_tavily.json
Needs  : TAVILY_API_KEY

  python3 scripts/03_research_tavily.py            # "cannot tell" rows
  python3 scripts/03_research_tavily.py --all
  python3 scripts/03_research_tavily.py --ids 3,5,8
"""
import argparse, json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import KIT, need_key, http, parse_brief, select_rows, site_for, norm_answer, run_parallel


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="work")
    ap.add_argument("--brief", default=str(KIT / "brief.md"))
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--ids")
    a = ap.parse_args()
    H = {"Authorization": "Bearer " + need_key("TAVILY_API_KEY")}
    tmpl = parse_brief(a.brief).get("RESEARCH_QUESTION") or sys.exit("RESEARCH_QUESTION line missing in brief.md")
    rows = select_rows(a.dir, a.ids, a.all)
    print(f"Tavily: {len(rows)} companies (about {len(rows)} credits)", flush=True)

    def one(c):
        q = tmpl.format(name=c["name"], website=site_for(c))
        t0 = time.time()
        try:
            res = http("POST", "https://api.tavily.com/search", H,
                       {"query": q, "search_depth": "basic", "max_results": 5,
                        "include_answer": "basic", "include_usage": True})
            text = res.get("answer") or ""
            r = {"id": c["id"], "name": c["name"], "tool": "tavily", "question": q,
                 "answer": norm_answer(text), "answer_text": text, "confidence": "",
                 "sources": [x["url"] for x in res.get("results", [])][:5],
                 "credits": (res.get("usage") or {}).get("credits"), "seconds": round(time.time() - t0)}
        except RuntimeError as e:
            r = {"id": c["id"], "name": c["name"], "tool": "tavily", "question": q, "answer": "cannot tell",
                 "answer_text": f"[error] {e}", "confidence": "", "sources": [], "credits": 0, "seconds": round(time.time() - t0)}
        print(f"  {r['id']:>3} {r['name']}: {r['answer']} ({r['seconds']}s)", flush=True)
        return r

    out = run_parallel(one, rows, a.workers)
    Path(a.dir, "research_tavily.json").write_text(json.dumps(out, indent=1))
    used = sum(r.get("credits") or 0 for r in out)
    errs = sum(1 for r in out if r["answer_text"].startswith("[error]"))
    print(f"Wrote {a.dir}/research_tavily.json: {len(out)} answers, {errs} errors, {used} credits used.")


if __name__ == "__main__":
    main()
