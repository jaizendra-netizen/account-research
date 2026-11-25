"""Small helpers shared by the scripts. Standard library only. Never prints a key."""
import csv, json, os, re, sys, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
UA = "account-research-kit/1.0"


def load_env():
    """Read KEY=value lines from .env (current folder, then the kit folder).
    Values already set in the environment win."""
    for p in (Path.cwd() / ".env", KIT / ".env"):
        if p.is_file():
            for line in p.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if v and k not in os.environ:
                    os.environ[k] = v


def need_key(name):
    load_env()
    v = os.environ.get(name, "").strip()
    if not v:
        sys.exit(f"Missing {name}. Put it in .env (see .env.example) or export it.")
    return v


def http(method, url, headers, body=None, timeout=120, retries=3):
    """JSON in, JSON out. Retries 429 and 5xx. The error text never includes the URL or headers."""
    data = json.dumps(body).encode() if body is not None else None
    h = {"User-Agent": UA, **headers}
    if body is not None:
        h.setdefault("Content-Type", "application/json")
    last = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=data, headers=h, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")[:300]
            last = RuntimeError(f"HTTP {e.code}: {msg}")
            if e.code in (429, 500, 502, 503, 504) and attempt < retries:
                time.sleep(3 * (attempt + 1))
                continue
            raise last
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last = RuntimeError(f"network error: {e}")
            if attempt < retries:
                time.sleep(3 * (attempt + 1))
                continue
            raise last
    raise last


def parse_brief(path):
    """The brief holds three marked lines: QUESTION:, RESEARCH_QUESTION:, SEARCH_QUERY:"""
    out = {}
    for line in Path(path).read_text().splitlines():
        m = re.match(r"^(QUESTION|RESEARCH_QUESTION|SEARCH_QUERY):\s*(.+?)\s*$", line)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def domain(url):
    """plaid.com from https://www.plaid.com/path ; keeps co.uk style endings."""
    u = (url or "").strip().lower()
    u = re.sub(r"^[a-z]+://", "", u).split("/")[0].split("?")[0].split(":")[0]
    u = re.sub(r"^www\.", "", u)
    parts = u.split(".")
    if len(parts) >= 3 and parts[-2] in ("co", "com", "org", "net", "ac", "gov") and len(parts[-1]) == 2:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:]) if len(parts) >= 2 else u


def norm_answer(text):
    """First word decides: yes / no / cannot tell."""
    t = (text or "").strip().lower().lstrip("*_#\"' ")
    if t.startswith("yes"):
        return "yes"
    if t.startswith("no") and not t.startswith("not "):
        return "no"
    return "cannot tell"


def select_rows(dir_, ids=None, everything=False):
    """Companies to research: the 'cannot tell' rows of judged.csv, or all, or the ids given."""
    companies = read_csv(Path(dir_) / "companies.csv")
    if ids:
        want = {i.strip() for i in ids.split(",")}
        return [c for c in companies if c["id"] in want]
    if everything:
        return companies
    jp = Path(dir_) / "judged.csv"
    if not jp.is_file():
        sys.exit(f"{jp} not found. Run the judging step first, or pass --all or --ids 1,2,3.")
    unsure = {r["id"] for r in read_csv(jp) if r["verdict"].strip().lower() == "cannot tell"}
    return [c for c in companies if c["id"] in unsure]


def site_for(c):
    """Prefer the website you expected over the one LinkedIn returned."""
    return (c.get("expected_website") or c.get("website") or "").strip()


def run_parallel(fn, items, workers):
    with ThreadPoolExecutor(workers) as ex:
        return list(ex.map(fn, items))
