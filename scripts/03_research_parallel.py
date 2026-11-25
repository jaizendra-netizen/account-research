#!/usr/bin/env python3
"""Step 3 (option A). Ask Parallel's Task API the sharp question about each unsure company.

Reads  : work/companies.csv, work/judged.csv, brief.md (the RESEARCH_QUESTION line)
Writes : work/research_parallel.json
Needs  : PARALLEL_API_KEY
Runs   : one Task run per company, several at once. Only the "cannot tell" rows by default.

  python3 scripts/03_research_parallel.py
  python3 scripts/03_research_parallel.py --all            # every company
  python3 scripts/03_research_parallel.py --ids 3,5,8      # just these
"""
import argparse, json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import KIT, need_key, http, parse_brief, select_rows, site_for, norm_answer, run_parallel

BASE = "https://api.parallel.ai/v1/tasks/runs"
SCHEMA = {"type": "json", "json_schema": {
    "type": "object",
    "properties": {"answer": {"type": "string", "description": "Exactly one of: yes, no, cannot tell"}},
    "required": ["answer"], "additionalProperties": False}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="work")
    ap.add_argument("--brief", default=str(KIT / "brief.md"))
    ap.add_argument("--processor", default="base", help="base is the one we tested; lite is cheaper, core and pro are deeper")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--ids")
    a = ap.parse_args()
    key = need_key("PARALLEL_API_KEY")
    H = {"x-api-key": key}
    tmpl = parse_brief(a.brief).get("RESEARCH_QUESTION") or sys.exit("RESEARCH_QUESTION line missing in brief.md")
    rows = select_rows(a.dir, a.ids, a.all)
    print(f"Parallel: {len(rows)} companies, processor {a.processor}, {a.workers} at a time", flush=True)

    def one(c):
        q = tmpl.format(name=c["name"], website=site_for(c))
        t0 = time.time()
        try:
            run = http("POST", BASE, H, {"input": q, "processor": a.processor, "task_spec": {"output_schema": SCHEMA}})
            res = None
            for _ in range(20):  # the result call waits up to `timeout` seconds, then we ask again
                try:
                    res = http("GET", f"{BASE}/{run['run_id']}/result?timeout=60", H, timeout=120, retries=1)
                    break
                except RuntimeError as e:
                    if "HTTP 408" in str(e) or "HTTP 504" in str(e) or "HTTP 202" in str(e):
                        continue
                    raise
            if res is None:
                raise RuntimeError("no result after 20 minutes")
            out = res.get("output") or {}
            content = out.get("content")
            if isinstance(content, str):
                try:
                    content = json.loads(content)
                except ValueError:
                    content = {"answer": content}
            text = (content or {}).get("answer", "")
            basis = out.get("basis") or []
            sources, reasoning, conf = [], "", ""
            for b in basis:
                for cit in b.get("citations", []):
                    if cit.get("url") and cit["url"] not in sources:
                        sources.append(cit["url"])
                reasoning = reasoning or b.get("reasoning", "")
                conf = conf or (b.get("confidence") or "")
            r = {"id": c["id"], "name": c["name"], "tool": "parallel", "question": q,
                 "answer": norm_answer(text), "answer_text": reasoning or text, "confidence": conf,
                 "sources": sources[:5], "run_id": run["run_id"], "seconds": round(time.time() - t0)}
        except RuntimeError as e:
            r = {"id": c["id"], "name": c["name"], "tool": "parallel", "question": q, "answer": "cannot tell",
                 "answer_text": f"[error] {e}", "confidence": "", "sources": [], "run_id": "", "seconds": round(time.time() - t0)}
        print(f"  {r['id']:>3} {r['name']}: {r['answer']} ({r['seconds']}s)", flush=True)
        return r

    t = time.time()
    out = run_parallel(one, rows, a.workers)
    Path(a.dir, "research_parallel.json").write_text(json.dumps(out, indent=1))
    errs = sum(1 for r in out if r["answer_text"].startswith("[error]"))
    print(f"Wrote {a.dir}/research_parallel.json: {len(out)} answers, {errs} errors, {round(time.time() - t)}s in total.")


if __name__ == "__main__":
    main()
