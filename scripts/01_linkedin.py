#!/usr/bin/env python3
"""Step 1. Get each company's own LinkedIn description.

Input  : work/companies.txt, one company per line:
           https://www.linkedin.com/company/plaid-/ | Plaid | plaid.com
         Only the URL is required. Name and website are what YOU expect; they are used to
         catch a LinkedIn address that points at the wrong company.
Output : work/linkedin_raw.json (the complete answer) and work/companies.csv
Needs  : APIFY_TOKEN  (not needed with --raw)

  python3 scripts/01_linkedin.py
  python3 scripts/01_linkedin.py --dir work --raw some_old_linkedin_raw.json   # no API call
"""
import argparse, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import need_key, http, domain, write_csv

ACTOR = "harvestapi~linkedin-company"
URL = f"https://api.apify.com/v2/acts/{ACTOR}/run-sync-get-dataset-items"


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def url_key(u):
    return (u or "").strip().lower().rstrip("/").replace("http://", "https://").replace("://www.", "://")


def read_list(path):
    rows = []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        rows.append({"url": parts[0],
                     "exp_name": parts[1] if len(parts) > 1 else "",
                     "exp_site": parts[2] if len(parts) > 2 else ""})
    return rows


def flags_for(want, item):
    f = []
    if item is None:
        return ["not_returned: LinkedIn gave nothing for this address"]
    name, site, desc = item.get("name") or "", item.get("website") or "", item.get("description") or ""
    if want["exp_name"]:
        a, b = norm(want["exp_name"]), norm(name)
        if a and b and a not in b and b not in a:
            f.append(f"name_mismatch: expected '{want['exp_name']}', got '{name}'")
    if want["exp_site"]:
        a, b = domain(want["exp_site"]), domain(site)
        if a != b:
            f.append(f"website_mismatch: expected {a}, got {b or 'none'}")
    if url_key(item.get("linkedinUrl")) != url_key(want["url"]):
        f.append(f"linkedin_url_changed: asked {want['url']}, got {item.get('linkedinUrl')}")
    if not desc.strip():
        f.append("no_description")
    elif len(desc.strip()) < 100:
        f.append(f"short_description: {len(desc.strip())} characters")
    return f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="work")
    ap.add_argument("--input", default=None, help="default: <dir>/companies.txt")
    ap.add_argument("--raw", default=None, help="use an existing linkedin_raw.json instead of calling Apify")
    ap.add_argument("--batch", type=int, default=25, help="companies per Apify call")
    a = ap.parse_args()
    d = Path(a.dir)
    d.mkdir(parents=True, exist_ok=True)
    wants = read_list(a.input or d / "companies.txt")
    if not wants:
        sys.exit("companies.txt is empty.")

    if a.raw:
        items = json.loads(Path(a.raw).read_text())
    else:
        token = need_key("APIFY_TOKEN")
        items = []
        for i in range(0, len(wants), a.batch):
            chunk = [w["url"] for w in wants[i:i + a.batch]]
            print(f"Apify: {i + 1}-{i + len(chunk)} of {len(wants)} ...", flush=True)
            items += http("POST", f"{URL}", {"Authorization": f"Bearer {token}"},
                          {"companies": chunk}, timeout=300)
        (d / "linkedin_raw.json").write_text(json.dumps(items, indent=1))

    by_query = {}
    for it in items:
        q = (it.get("originalQuery") or {}).get("search")
        by_query[url_key(q)] = it
    rows = []
    for n, w in enumerate(wants, 1):
        it = by_query.get(url_key(w["url"]))
        rows.append({
            "id": n,
            "name": (it or {}).get("name") or w["exp_name"] or w["url"],
            "website": (it or {}).get("website") or "",
            "expected_website": w["exp_site"],
            "employees": (it or {}).get("employeeCount") or "",
            "description": re.sub(r"\s+", " ", (it or {}).get("description") or "").strip(),
            "linkedin_url": (it or {}).get("linkedinUrl") or w["url"],
            "flags": " ; ".join(flags_for(w, it)),
        })
    write_csv(d / "companies.csv", rows, ["id", "name", "website", "expected_website", "employees",
                                          "description", "linkedin_url", "flags"])
    flagged = [r for r in rows if r["flags"]]
    print(f"Wrote {d / 'companies.csv'}: {len(rows)} companies, {len(flagged)} with flags.")
    for r in flagged:
        print(f"  {r['id']:>3} {r['name']}: {r['flags']}")


if __name__ == "__main__":
    main()
