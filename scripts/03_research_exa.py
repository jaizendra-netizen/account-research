#!/usr/bin/env python3
"""Step 3 (option C). Ask Exa's Answer endpoint the sharp question about each unsure company.

Exa /answer searches the web and writes a short answer with the pages it used.

Reads  : work/companies.csv, work/judged.csv, brief.md (the RESEARCH_QUESTION line)
Writes : work/research_exa.json
Needs  : EXA_API_KEY

  python3 scripts/03_research_exa.py            # "cannot tell" rows
  python3 scripts/03_research_exa.py --all
  python3 scripts/03_research_exa.py --ids 3,5,8
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
    H = {"x-api-key": need_key("EXA_API_KEY")}
    tmpl = parse_brief(a.brief).get("RESEARCH_QUESTION") or sys.exit("RESEARCH_QUESTION line missing in brief.md")
    rows = select_rows(a.dir, a.ids, a.all)
    print(f"Exa: {len(rows)} companies", flush=True)

    def one(c):
        q = tmpl.format(name=c["name"], website=site_for(c))
        t0 = time.time()
        try:
            res = http("POST", "https://api.exa.ai/answer", H, {"query": q})
            ans = res.get("answer")
            text = ans if isinstance(ans, str) else json.dumps(ans)
            r = {"id": c["id"], "name": c["name"], "tool": "exa", "question": q,
                 "answer": norm_answer(text), "answer_text": text, "confidence": "",
                 "sources": [x.get("url") for x in res.get("citations", []) if x.get("url")][:5],
                 "cost_dollars": (res.get("costDollars") or {}).get("total"), "seconds": round(time.time() - t0)}
        except RuntimeError as e:
            r = {"id": c["id"], "name": c["name"], "tool": "exa", "question": q, "answer": "cannot tell",
                 "answer_text": f"[error] {e}", "confidence": "", "sources": [], "cost_dollars": 0, "seconds": round(time.time() - t0)}
        print(f"  {r['id']:>3} {r['name']}: {r['answer']} ({r['seconds']}s)", flush=True)
        return r

    out = run_parallel(one, rows, a.workers)
    Path(a.dir, "research_exa.json").write_text(json.dumps(out, indent=1))
    spent = sum(r.get("cost_dollars") or 0 for r in out)
    errs = sum(1 for r in out if r["answer_text"].startswith("[error]"))
    print(f"Wrote {a.dir}/research_exa.json: {len(out)} answers, {errs} errors, about ${spent:.3f} spent.")


if __name__ == "__main__":
    main()
