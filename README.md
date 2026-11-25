# Account research with Claude Code

By Jainendra Ojha, Agentic GTM.

You give it a list of companies and one yes/no question. It does five things:

1. Gets each company's own LinkedIn description.
2. Has Claude judge from that text: a verdict, a reason, the exact quote and a confidence.
3. For every "cannot tell", asks a web research tool the question directly and keeps its sources.
4. Marks rows where the LinkedIn page looks like the wrong company.
5. Writes one `results.csv` that says, for each row, where the answer came from.

No Anthropic API key is used anywhere. Claude Code does the judging with your own login.

What is in the folder:

```
README.md                          this file
brief.md                           your question lives here (one marked block)
.env.example                       the names of the keys
.claude/skills/account-research/   the Claude Code skill: type "research these accounts"
scripts/                           plain Python 3, standard library only
examples/                          a real run on 18 public companies, every file
```

Tested with Python 3.9 on a Mac (the web-service scripts) and 3.15 (the offline scripts), and Claude Code 2.1.304. The scripts have no packages to install.

## Setup

### 1. Get the folder

Download or clone this folder, then:

```bash
cd account-research
```

### 2. Get the keys

You need the first key, and at least one of the other four.

| Key | What it does here | Sign up | Variable in `.env` |
|---|---|---|---|
| Apify | Pulls each LinkedIn company page | https://console.apify.com/sign-up, then copy your token from https://console.apify.com/settings/integrations | `APIFY_TOKEN` |
| Parallel | Researches a question on the web, with sources | https://platform.parallel.ai | `PARALLEL_API_KEY` |
| Tavily | Web search that returns a short answer and its pages | https://app.tavily.com | `TAVILY_API_KEY` |
| Exa | Web search that returns an answer and citations | https://dashboard.exa.ai/api-keys | `EXA_API_KEY` |
| Serper | Google's own results page as data | https://serper.dev | `SERPER_API_KEY` |

Tavily's reference page (read 13 Nov 2026) says the free plan has 1,000 credits a month and needs no card.
Check each site for its current free plan and prices. They change.

### 3. Put them in `.env`

```bash
cp .env.example .env
```

Open `.env` in any editor and paste each key after its `=`. The scripts read `.env` themselves.
`.env` is in `.gitignore`. Never commit it.

Check which keys the scripts can see (this prints names only, never the keys):

```bash
for k in APIFY_TOKEN PARALLEL_API_KEY TAVILY_API_KEY EXA_API_KEY SERPER_API_KEY; do
  if grep -q "^$k=.\+" .env 2>/dev/null || [ -n "$(printenv $k)" ]; then echo "$k: set"; else echo "$k: missing"; fi
done
```

### 4. Claude Code

Install Claude Code and log in. Judging uses your login (`claude -p`), not an API key.
If you want it counted against your subscription and not an API bill, run `unset ANTHROPIC_API_KEY`
in the terminal first.

## Run it

Everything runs from this folder. Your files go in `work/`.

### Step 1. Your companies

Make the folder and the list. One company per line. Only the LinkedIn address is required. The two
columns after the bars are what YOU expect the company to be called and its website. They are how
the kit catches a LinkedIn address that points at the wrong company.

```bash
mkdir -p work
cat > work/companies.txt <<'EOF'
https://www.linkedin.com/company/plaid-/ | Plaid | plaid.com
https://www.linkedin.com/company/blend/ | Blend | blend.com
EOF
```

To try the kit on the 18 public companies from `examples/` instead:

```bash
mkdir -p work && cp examples/companies.txt work/companies.txt
```

### Step 2. Your question

Open `brief.md`. Edit only the marked block. The file is already filled with a working example
("Does this company sell software to banks, insurers or lenders?"). It has three lines:

- `QUESTION:` what Claude answers from each company's LinkedIn text.
- `RESEARCH_QUESTION:` the same question, sharper, for the web research tool. It must carry the
  company name, the website, what counts as "no", and "yes or no first". Keep `{name}` and `{website}`.
- `SEARCH_QUERY:` a short Google query. Only the Serper script uses it.

Also change the "Who we are" line.

### Step 3. Get the LinkedIn text

```bash
python3 scripts/01_linkedin.py
```

It writes `work/linkedin_raw.json` (the complete answer from Apify, keep it) and `work/companies.csv`.
Read the flags it prints. A flagged row is a company to check before you trust any verdict about it.

To rebuild `companies.csv` from a saved pull without paying again:

```bash
python3 scripts/01_linkedin.py --raw work/linkedin_raw.json
```

### Step 4. Judge from the LinkedIn text

Open Claude Code in this folder (`claude`) and paste:

```
Follow scripts/02_judge.md and brief.md for the companies in work/companies.csv, 20 at a time.
Write work/judged.csv with the columns id,name,verdict,reason,quote,confidence.
Then run: python3 scripts/02_judge.py --check work/judged.csv
```

Or do the same step from the terminal, without opening Claude Code:

```bash
python3 scripts/02_judge.py
```

The check keeps Claude honest. A yes or no whose quote is not found word for word in the
company's text becomes "cannot tell". No quote, no verdict.

### Step 5. Research the "cannot tell" rows

Pick one tool, or run several to compare. Each one works only on the "cannot tell" rows.
Add `--all` for every company, or `--ids 3,5` for chosen rows.

```bash
python3 scripts/03_research_parallel.py
```

```bash
python3 scripts/03_research_exa.py
```

```bash
python3 scripts/03_research_tavily.py
```

```bash
python3 scripts/03_search_serper.py
```

### Step 6. Read the answers that are not a clean yes or no

Parallel and Exa answer yes or no. Tavily often answers in a sentence. Serper returns only Google
results. Claude reads those. In Claude Code:

```
Follow scripts/03_review.md for the research answers in work/research_*.json that are not a clean yes or no.
Write work/research_review.csv with the columns id,tool,verdict,reason.
```

Or from the terminal:

```bash
python3 scripts/02_judge.py --review
```

If every answer was already yes or no, the script says "Nothing to review". That is fine.

### Step 7. Merge

```bash
python3 scripts/04_merge.py
```

It writes `work/results.csv` and prints the counts and the rows that need a look.

### The short way

In Claude Code, in this folder, type:

```
research these accounts
```

The skill in `.claude/skills/account-research/SKILL.md` asks for your question and your companies,
tells you what each step will cost, and runs the scripts above in order.

## What you get

This is the real run in `examples/`: 18 public companies, the question "Does this company sell
software to banks, insurers or lenders?", Parallel for the research step.

| Company | Final verdict | Came from | Needs review |
|---|---|---|---|
| Plaid | no | parallel research | |
| Guidewire Software | yes | linkedin text | |
| Marqeta | no | parallel research | |
| Duck Creek Technologies | yes | linkedin text | |
| Figma | no | parallel research | yes |
| Q2 | yes | linkedin text | |
| Jack Henry | yes | linkedin text | |
| Notion | no | parallel research | |
| MeridianLink | yes | linkedin text | |
| Asana | no | parallel research | |
| BLEND | no | linkedin text | yes |
| Toast | no | linkedin text | |
| Procore Technologies | no | linkedin text | |
| Canva | no | parallel research | |
| Veeva Systems | no | linkedin text | |
| Datadog | no | linkedin text | |
| Shopify | no | linkedin text | |
| HubSpot | no | parallel research | |

Counts: 5 yes, 13 no. Judging the LinkedIn text alone gave 5 yes, 6 no, 7 cannot tell. The research
step settled all 7.

Two rows are marked for review, and both are right to be:

- BLEND: `website_mismatch: expected blend.com, got blendcompany.com`. The LinkedIn address `/company/blend/`
  belongs to a fashion company, not the mortgage software company we meant. The verdict "no" is correct
  for the page it read and useless for the company we wanted. Find the right address and run again.
- Figma: `website_mismatch: expected figma.com, got figma.bot` and a 21-character description. This is
  the right company with a poor LinkedIn page. It is a false alarm, and the research step answered it.

A row, from `examples/results.csv` (trimmed):

```
name:            Jack Henry
final_verdict:   yes
evidence_from:   linkedin text
quote:           Approximately 7,500 community and regional banks and credit unions count on us
confidence:      high
```

```
name:            Plaid
verdict_linkedin: cannot tell
final_verdict:   no
evidence_from:   parallel research
parallel_note:   Plaid describes its core offering as APIs connecting consumers, financial institutions,
                 and developers ... this supports that it is a general tool rather than a product
                 built specifically for banks, insurers, or lenders.
parallel_sources: https://plaid.com/build-with-plaid https://plaid.com/what-is-plaid
```

Columns of `results.csv`: `id, name, website, employees, final_verdict, evidence_from, needs_review,
check, verdict_linkedin, reason, quote, quote_in_text, confidence`, then `<tool>_answer`,
`<tool>_note`, `<tool>_sources` for every research tool you ran.

Every file of that run is in `examples/`: the input, `linkedin_raw.json`, `companies.csv`,
`judged.csv`, one `research_*.json` per tool, `research_review.csv` and `results.csv`.

What the other three tools said on the same 7 rows (all in `examples/`):

| Tool | Rows | Clean yes/no answers | Notes |
|---|---|---|---|
| Parallel | 7 | 7 (all no) | 7 runs at once took 45 s in one run, 68 s in the next |
| Exa | 7 | 7 (all no) | about 1 to 2 s each |
| Tavily | 7 | 3 | the other 4 were sentences that Claude read as "no" |
| Serper | 7 | 0 (it gives no answers) | Claude read the snippets: 5 no, 2 cannot tell (Marqeta, Canva) |

## When it goes wrong

Each row is something that happened in our tests.

| Symptom | Cause | Fix |
|---|---|---|
| A verdict about the wrong company. "Blend" came back as a fashion brand. | The LinkedIn address is real but belongs to another company with the same name. | Give the kit the name and website you expect in `companies.txt`. Step 3 flags `website_mismatch`. Check every flagged row. |
| `short_description` flag. Figma's page said "Trying all the skills". | The company wrote almost nothing on LinkedIn. | Expect "cannot tell". The research step handles it. |
| `linkedin_url_changed` flag. Q2's old address now points at a new page. | LinkedIn redirected it. | Usually harmless. Check that the name still fits. |
| Reading each company's homepage did not help. In our test, all 8 "cannot tell" rows stayed "cannot tell". (`examples/homepage_test/`) | A homepage says what a company does, often not who it sells to. | The kit does not read homepages. It asks a research tool the question. |
| The research tool says "yes" for everything. With the loose question "does X sell software to banks?" it said yes for all 8, including Figma and Canva. It also mixed up Notion with another company called Notion. (`examples/question_test/loose_question_answers.json`) | A loose question is answered by any one bank that uses the tool. A name alone can mean two companies. | Write the sharp question: the name, the website, "a general tool that some banks also use counts as no", and "yes or no first". The sharp version fixed all 8. (`examples/question_test/sharp_question_answers.json`) |
| The sharp question gives a different answer from the plain one. | It is a narrower question: "built specifically for" is stricter than "sells to". Plaid is the example. | Decide which one you mean and write it in both lines of `brief.md`. |
| Claude says "no" for a general tool because the text is silent. | Silence is not a no. With the first brief we tried, a headless Claude run gave 3 "cannot tell". The run we had made in Claude Code gave 8. | `scripts/02_judge.md` says a "no" must be earned by text naming other customers. With that rule, 7 "cannot tell". |
| Claude's quote is not in the company's text. | It paraphrased or made it up. | `02_judge.py --check` turns that verdict into "cannot tell" and says why in the reason. |
| Tavily's answer is a sentence, not yes or no. 4 of 7 in both of our runs. | Tavily's answer follows its own wording. | Step 6. Claude reads the sentence. |
| Serper gives no answer. | It is a Google results page, not a research tool. | Step 6. Claude reads the snippets. Treat it as weaker evidence than Parallel or Exa. |
| `claude -p failed: Not logged in` | Claude Code is not logged in for this user. | Run `claude` once and log in. |
| `The claude command was not found` | Claude Code is not on your PATH. | Install it, or do Step 4 inside Claude Code with the prompt in this README. |
| `HTTP 402` or "not enough credits" from a tool | The key's balance or monthly limit is used up. | Top up, or use another tool. We hit this with one Serper key: the error was `Not enough credits` and no search was charged. |
| `HTTP 429` | Too many requests at once. | The scripts retry. Lower `--workers`. |
| One research row says `[error] ...` | The call failed after retries. | Re-run with `--ids <id>`. |
| A tool says "yes" because a general vendor has a "solutions for banks" page. Tavily did this for Datadog in our skill test: it cited Datadog's own financial-services page. | The page proves some banks use the tool, not that it is built for banks. | Read the sources of every research "yes". Consider adding "a solutions page for banks on a general vendor's site counts as no" to `RESEARCH_QUESTION`. We have not tested that sentence. |
| The judge is not repeatable. Plaid was "cannot tell" in one run, "no" in another, and "yes" (medium confidence, quote "many of the largest banks") in a Claude Code session. | Claude's reading of vague text differs between runs and models. | Keep the quotes. Run the 20 companies you know first and read every reason. Use `needs_review` and the research step as the second check. |
| Tools disagree on a row. | Different pages, different readings. | `needs_review` is set and `check` lists who said what. Read the sources. |

## What it costs (measured, 25 Nov 2026)

| Step | Cost |
|---|---|
| Apify LinkedIn pull | $0.004 a company. Two runs on Apify's own usage record: 3 companies $0.012, 18 companies $0.072. So 500 companies is about $2. |
| Claude judging | Your Claude Code login. |
| Tavily | 1 credit a search. |
| Serper | 1 credit a search. |
| Exa Answer | $0.005 an answer (the `costDollars` field of each response). |
| Parallel Task | Priced per run by processor. Their pricing page (read 13 Apr 2026) says $0.005 to $2.40 a request. We used the `base` processor and did not read our spend per run. |

You only pay for research on the "cannot tell" rows.

## The five tools

Each section: the job, the one endpoint the kit uses, a copy-paste `curl`, and the shape of a real
answer (trimmed). Replace the placeholder key. The `curl` blocks for Parallel, Tavily, Exa and Serper
were each run with a real key on 25 Nov 2026 and returned the responses shown. The Apify block is
explained in its own section.

### Apify: the LinkedIn company page

- **Job:** the company's own About text, website and headcount, from the actor `harvestapi/linkedin-company`.
- **Endpoint:** `POST https://api.apify.com/v2/acts/harvestapi~linkedin-company/run-sync-get-dataset-items`
- **Kit script:** `scripts/01_linkedin.py`. It sends 25 companies per call.

```bash
curl -s -X POST "https://api.apify.com/v2/acts/harvestapi~linkedin-company/run-sync-get-dataset-items" \
  -H "Authorization: Bearer YOUR_APIFY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"companies": ["https://www.linkedin.com/company/plaid-/"]}'
```

Not run by us as a `curl`. We ran `scripts/01_linkedin.py`, which sends this same request (same address,
same header, same body), once with 3 companies. A free `curl` check that your token works:

```bash
curl -s "https://api.apify.com/v2/users/me/limits" -H "Authorization: Bearer YOUR_APIFY_TOKEN"
```

(We ran that one. It returns JSON with a `limits` block and a `current` block.)

Shape of the answer, a list with one object per company (trimmed from `examples/linkedin_raw.json`):

```json
[
  {
    "id": "2684737",
    "universalName": "plaid-",
    "linkedinUrl": "https://www.linkedin.com/company/plaid-/",
    "name": "Plaid",
    "website": "https://plaid.com",
    "employeeCount": 1706,
    "followerCount": 271296,
    "companyType": "Privately Held",
    "tagline": "On a mission to unlock financial freedom for everyone. Join us!",
    "description": "Plaid is a data network that powers the tools millions of people rely on to live a healthier financial life. Plaid works with thousands of companies like Venmo, SoFi, and Betterment ...",
    "originalQuery": {"search": "https://www.linkedin.com/company/plaid-/", "location": ""}
  }
]
```

`originalQuery.search` is the address you sent. The kit uses it to match each answer to its row.
`linkedinUrl` can differ from it when LinkedIn has redirected the page.

### Parallel: research a question, with sources

- **Job:** takes a question, searches and reads the web, returns a structured answer with citations.
- **Endpoint:** `POST https://api.parallel.ai/v1/tasks/runs` to start, then
  `GET https://api.parallel.ai/v1/tasks/runs/RUN_ID/result` to read.
- **Kit script:** `scripts/03_research_parallel.py`. One run per company, 8 at a time.

Start a run:

```bash
curl -s -X POST "https://api.parallel.ai/v1/tasks/runs" \
  -H "x-api-key: YOUR_PARALLEL_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "About the company Notion (website notion.com): is its main product built specifically for banks, insurers or lenders? A general tool that some banks also use counts as no. Answer yes, no or cannot tell first, then one sentence of evidence.",
    "processor": "base",
    "task_spec": {"output_schema": {"type": "json", "json_schema": {
      "type": "object",
      "properties": {"answer": {"type": "string", "description": "Exactly one of: yes, no, cannot tell"}},
      "required": ["answer"], "additionalProperties": false}}}
  }'
```

It answers at once with the run id (trimmed, real):

```json
{"run_id": "trun_28a0f9ec3d4f47cc9a25d75d01b0a351", "status": "queued", "is_active": true, "processor": "base"}
```

Read the result. Put the `run_id` in place of `RUN_ID`. It waits up to `timeout` seconds. It took
about 40 seconds:

```bash
curl -s "https://api.parallel.ai/v1/tasks/runs/RUN_ID/result?timeout=120" \
  -H "x-api-key: YOUR_PARALLEL_KEY"
```

Real answer (trimmed):

```json
{
  "run": {"run_id": "trun_28a0f9ec3d4f47cc9a25d75d01b0a351", "status": "completed", "processor": "base"},
  "output": {
    "type": "json",
    "content": {"answer": "no"},
    "basis": [{
      "field": "answer",
      "citations": [{"title": "What is Notion? | Notion", "url": "https://www.notion.com/product/notion",
                     "excerpts": ["Notion is a connected workspace that brings docs, wikis, projects, and databases together in one place. ..."]}],
      "reasoning": "Notion describes its product as a connected workspace combining documents, wikis, projects, and databases, which supports that it is a general-purpose tool rather than one built specifically for banks, insurers, or lenders.",
      "confidence": "medium"
    }]
  }
}
```

The answer is in `output.content`. The reasons, sources and confidence are in `output.basis`. Do not add
an `evidence` field to your schema: Parallel warns that `basis` already carries it.

### Tavily: search with a written answer

- **Job:** web search that also writes a short answer from the pages it found.
- **Endpoint:** `POST https://api.tavily.com/search`
- **Kit script:** `scripts/03_research_tavily.py`. 1 credit per company at `search_depth: basic`.

```bash
curl -s -X POST "https://api.tavily.com/search" \
  -H "Authorization: Bearer YOUR_TAVILY_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "About the company Notion (website notion.com): is its main product built specifically for banks, insurers or lenders? A general tool that some banks also use counts as no. Answer yes, no or cannot tell first, then one sentence of evidence.",
    "search_depth": "basic",
    "max_results": 5,
    "include_answer": "basic",
    "include_usage": true
  }'
```

Real answer (trimmed):

```json
{
  "query": "About the company Notion (website notion.com): is its main product built specifically ...",
  "answer": "The sources indicate that Notion is not built specifically for banks, insurers, or lenders. Instead, it is a generalist tool designed to be a flexible workspace for a wide range of users ...",
  "results": [
    {"url": "https://www.taskade.com/blog/notion-review", "title": "Notion Review 2026: Is Notion Still Worth It? Pros & Cons", "content": "## What is Notion?\n\nNotion is the connected workspace that redefined how teams organize docs, databases, and wikis ...", "score": 0.21109138},
    {"url": "https://research.contrary.com/report/notion", "title": "Report: Notion Business Breakdown & Founding Story | Contrary Research", "content": "## Product\n\nNotion is designed to serve as an all-in-one workspace and productivity tool ...", "score": 0.20979328}
  ],
  "usage": {"credits": 1}
}
```

Note that the answer does not start with "no", although we asked for that. This is why Step 6 exists.

### Exa: answer with citations

- **Job:** searches by meaning and writes an answer, with the pages it used.
- **Endpoint:** `POST https://api.exa.ai/answer`
- **Kit script:** `scripts/03_research_exa.py`.

```bash
curl -s -X POST "https://api.exa.ai/answer" \
  -H "x-api-key: YOUR_EXA_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "About the company Notion (website notion.com): is its main product built specifically for banks, insurers or lenders? A general tool that some banks also use counts as no. Answer yes, no or cannot tell first, then one sentence of evidence."}'
```

Real answer (trimmed):

```json
{
  "requestId": "360473f9ec3625cb861a98b892cf27f1",
  "answer": "No. Notion is a general-purpose, cloud-based collaborative workspace designed to function as an all-in-one tool for documentation, project management, and knowledge organization across diverse industries and team types.",
  "citations": [
    {"url": "https://www.notion.com/product/notion", "title": "What is Notion? | Notion"}
  ],
  "costDollars": {"total": 0.005}
}
```

Exa's reference page (read 13 Apr 2026) lists Answer at $5 per 1,000 requests. That matches the
`costDollars` we saw.

### Serper: Google's results as data

- **Job:** the Google results page for a query, as JSON. It does not answer questions. It shows
  what Google shows.
- **Endpoint:** `POST https://google.serper.dev/search`
- **Kit script:** `scripts/03_search_serper.py`. 1 credit per search. Claude then reads the snippets (Step 6).

```bash
curl -s -X POST "https://google.serper.dev/search" \
  -H "X-API-KEY: YOUR_SERPER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"q": "Notion notion.com customers banks insurers lenders", "num": 6, "gl": "us", "hl": "en"}'
```

Real answer (trimmed to the first two results):

```json
{
  "searchParameters": {"q": "Notion notion.com customers banks insurers lenders", "gl": "us", "hl": "en", "type": "search", "num": 6, "engine": "google"},
  "organic": [
    {"title": "Notion: A shared brain for your team and agents.", "link": "https://www.notion.com/", "snippet": "Notion is where your company's knowledge and context lives so your team and agents can get more done, faster.", "position": 1},
    {"title": "BankSync", "link": "https://www.notion.com/connections/banksync", "snippet": "Sync your banking data from over 10k+ institutions into Notion. BankSync is your secure banking data bridge that automatically syncs your financial information ...", "position": 2}
  ],
  "credits": 1
}
```

Some queries also return `answerBox`, `knowledgeGraph` or `peopleAlsoAsk`. The script keeps the answer box
when it is there.

## Notes on how it was tested

- Python 3.9 was the interpreter for the end-to-end run, started from a clean shell (`env -i`) with only
  the keys it needed. `01_linkedin.py --raw`, `02_judge.py --check` and `04_merge.py` also ran under 3.15 and gave
  identical files. The scripts that call a web service ran under 3.9 only.
- `01_linkedin.py` ran live once, on 3 companies. The 18-company example uses the saved Apify answer
  from our first test (`--raw`). The flags it raised (Blend, Figma, Q2) are the same in both.
- `02_judge.py`, the four research scripts, `--review`, `--check` and `04_merge.py` all ran end to end on
  the 18 companies, and the results are the files in `examples/`.
- Exa was run with a real key. Nothing in this kit is untested except what is listed here: the
  Apify `curl` was not run as a `curl` (see above).
- The prompts in Steps 4 and 6 were not pasted word for word into an interactive session. The skill run below
  did the same steps. The `--all` flag was not run. `--ids` was.
- The skill was run once, headless, with `claude -p "research these accounts ..."` in a copy of this
  folder with a ready `work/companies.csv` and only a Tavily key. It read the brief, judged, ran the
  quote check, ran Tavily, read the answers, merged, and reported counts, flags and spend. It took 2 minutes 23
  seconds. Its numbers differed from the run in `examples/` (6 yes, 11 no, 1 cannot tell), because
  judging by Claude varies from run to run (see the table above).
- The numbers in the example are one run. Another run may move a few companies between "no" and
  "cannot tell". The quote check and the research step are there to catch that.
