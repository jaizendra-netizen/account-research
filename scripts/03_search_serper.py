#!/usr/bin/env python3
"""Step 3 (option D). Google the company with Serper and keep the results.

Serper does not answer questions. It returns what Google shows: results with snippets, and
sometimes an answer box. So this step has two halves:
  1. this script saves the results for each unsure company;
  2. Claude reads them:  python3 scripts/02_judge.py --review     (or Claude Code does it itself,
     following scripts/03_review.md)

Reads  : work/companies.csv, work/judged.csv, brief.md (the SEARCH_QUERY line)
Writes : work/research_serper.json
Needs  : SERPER_API_KEY
1 credit per search.

  python3 scripts/03_search_serper.py            # "cannot tell" rows
  python3 scripts/03_search_serper.py --all
  python3 scripts/03_search_serper.py --ids 3,5,8
"""
import argparse, json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import KIT, need_key, http, parse_brief, select_rows, site_for, run_parallel


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="work")
    ap.add_argument("--brief", default=str(KIT / "brief.md"))
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--num", type=int, default=6, help="results per search")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--ids")
    a = ap.parse_args()
    H = {"X-API-KEY": need_key("SERPER_API_KEY")}
    tmpl = parse_brief(a.brief).get("SEARCH_QUERY") or sys.exit("SEARCH_QUERY line missing in brief.md")
    rows = select_rows(a.dir, a.ids, a.all)
    print(f"Serper: {len(rows)} searches (about {len(rows)} credits)", flush=True)

    def one(c):
        q = tmpl.format(name=c["name"], website=site_for(c))
        t0 = time.time()
        try:
            res = http("POST", "https://google.serper.dev/search", H, {"q": q, "num": a.num, "gl": "us", "hl": "en"})
            hits = [{"title": x.get("title", ""), "link": x.get("link", ""), "snippet": x.get("snippet", "")}
                    for x in res.get("organic", [])]
            box = res.get("answerBox") or {}
            box_text = box.get("answer") or box.get("snippet") or ""
            r = {"id": c["id"], "name": c["name"], "tool": "serper", "query": q, "answer": "", "answer_text": box_text,
                 "sources": [h["link"] for h in hits][:5], "results": hits,
                 "credits": res.get("credits"), "seconds": round(time.time() - t0)}
        except RuntimeError as e:
            r = {"id": c["id"], "name": c["name"], "tool": "serper", "query": q, "answer": "",
                 "answer_text": f"[error] {e}", "sources": [], "results": [], "credits": 0, "seconds": round(time.time() - t0)}
        print(f"  {r['id']:>3} {r['name']}: {len(r['results'])} results ({r['seconds']}s)", flush=True)
        return r

    out = run_parallel(one, rows, a.workers)
    Path(a.dir, "research_serper.json").write_text(json.dumps(out, indent=1))
    used = sum(r.get("credits") or 0 for r in out)
    print(f"Wrote {a.dir}/research_serper.json: {len(out)} searches, {used} credits used.")
    print("Next: python3 scripts/02_judge.py --review   (Claude reads the results)")


if __name__ == "__main__":
    main()
