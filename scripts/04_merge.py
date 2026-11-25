#!/usr/bin/env python3
"""Step 4. Merge everything into one results.csv.

Reads  : work/companies.csv, work/judged.csv
         and, if they exist: work/research_parallel.json, research_exa.json, research_tavily.json,
         research_serper.json, and research_review.csv (Claude's reading of answers that were not a clean yes/no)
Writes : work/results.csv

The final verdict is the LinkedIn verdict when it is yes or no. If it was "cannot tell", the first
research tool with a yes or no answers it (order: parallel, exa, tavily, serper). Rows where the
tools disagree, a tool failed, or the LinkedIn page looked like the wrong company are marked
needs_review = yes.

  python3 scripts/04_merge.py
"""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import read_csv, write_csv

ORDER = ["parallel", "exa", "tavily", "serper"]
RISKY = ("website_mismatch", "name_mismatch", "not_returned", "no_description")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="work")
    a = ap.parse_args()
    d = Path(a.dir)
    companies = read_csv(d / "companies.csv")
    judged = {r["id"]: r for r in read_csv(d / "judged.csv")}

    research = {}  # tool -> id -> dict(answer, note, sources)
    for tool in ORDER:
        p = d / f"research_{tool}.json"
        if not p.is_file():
            continue
        research[tool] = {}
        for r in json.loads(p.read_text()):
            research[tool][r["id"]] = {"answer": r.get("answer", ""), "note": r.get("answer_text", ""),
                                       "sources": " ".join(r.get("sources", []))}
    rv = d / "research_review.csv"
    if rv.is_file():
        for r in read_csv(rv):
            x = research.get(r["tool"], {}).get(r["id"])
            if x:
                x["answer"] = r["verdict"]
                x["note"] = (x["note"] + " || READ BY CLAUDE: " if x["note"] else "READ BY CLAUDE: ") + r["reason"]
    tools = [t for t in ORDER if t in research]

    out = []
    for c in companies:
        j = judged.get(c["id"], {})
        row = {"id": c["id"], "name": c["name"], "website": c["website"], "employees": c["employees"],
               "verdict_linkedin": j.get("verdict", ""), "reason": j.get("reason", ""), "quote": j.get("quote", ""),
               "quote_in_text": j.get("quote_in_text", ""), "confidence": j.get("confidence", "")}
        checks = [f.strip() for f in c.get("flags", "").split(" ; ") if f.strip()]
        review = any(f.startswith(RISKY) for f in checks)
        answers = {}
        for t in tools:
            x = research[t].get(c["id"])
            if x:
                row[f"{t}_answer"], row[f"{t}_note"], row[f"{t}_sources"] = x["answer"], x["note"], x["sources"]
                answers[t] = x["answer"]
                if x["note"].startswith("[error]"):
                    checks.append(f"{t} failed"); review = True
        v = j.get("verdict", "cannot tell")
        if v in ("yes", "no"):
            row["final_verdict"], row["evidence_from"] = v, "linkedin text"
        else:
            pick = next((t for t in tools if answers.get(t) in ("yes", "no")), None)
            if pick:
                row["final_verdict"], row["evidence_from"] = answers[pick], f"{pick} research"
            else:
                row["final_verdict"], row["evidence_from"] = "cannot tell", "none"
            decided = {t: a_ for t, a_ in answers.items() if a_ in ("yes", "no")}
            if len(set(decided.values())) > 1:
                checks.append("tools disagree: " + ", ".join(f"{t}={a_}" for t, a_ in decided.items())); review = True
        row["needs_review"] = "yes" if review else ""
        row["check"] = " ; ".join(checks)
        out.append(row)

    fields = ["id", "name", "website", "employees", "final_verdict", "evidence_from", "needs_review", "check",
              "verdict_linkedin", "reason", "quote", "quote_in_text", "confidence"]
    for t in tools:
        fields += [f"{t}_answer", f"{t}_note", f"{t}_sources"]
    write_csv(d / "results.csv", out, fields)
    n = {k: sum(1 for r in out if r["final_verdict"] == k) for k in ("yes", "no", "cannot tell")}
    src = {}
    for r in out:
        src[r["evidence_from"]] = src.get(r["evidence_from"], 0) + 1
    print(f"Wrote {d / 'results.csv'}: {len(out)} companies. {n['yes']} yes, {n['no']} no, {n['cannot tell']} cannot tell.")
    print("Evidence from: " + ", ".join(f"{k} {v}" for k, v in sorted(src.items())))
    flagged = [r for r in out if r["needs_review"]]
    print(f"{len(flagged)} marked needs_review" + (":" if flagged else "."))
    for r in flagged:
        print(f"  {r['id']:>3} {r['name']}: {r['check']}")


if __name__ == "__main__":
    main()
