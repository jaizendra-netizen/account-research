---
name: account-research
description: Research a list of companies against one yes/no question. Pulls each company's own LinkedIn description, has Claude judge it with a verdict, reason, exact quote and confidence, asks a web research tool (Parallel, Tavily, Exa or Serper) about the "cannot tell" rows, and writes one results.csv. Use when the user says "research these accounts", "qualify this company list", "which of these companies sell to X", or gives a list of LinkedIn company pages and a question.
---

# Account research

You turn a list of companies and ONE yes/no question into `work/results.csv`.
Every verdict carries a reason and the exact words it rests on.

Run everything from the folder that contains `scripts/` and `brief.md`. Data lives in `work/`.
The scripts are plain Python 3. Keys live in `.env`. Never print a key, never write one into a file
other than `.env`.

## Rules (they come from measured failures)

1. **One question per run.** Two questions in one pass give a muddled answer.
2. **Judge only from the text the scripts gave you.** Never from what you remember about a company.
   Never from an industry label.
3. **No quote, no verdict.** A yes or no must quote the company's own words, letter for letter.
   "Cannot tell" is a good answer. Silence is not a "no": a general tool whose text names no
   customers is "cannot tell".
4. **Check the company before you trust a row.** A LinkedIn address can point at a different
   company with the same name. Step 1 flags this. Show every flagged row to the user.
5. **Ask the research tool a sharp question:** the company name, its website, what counts as "no",
   and the answer order (yes or no first). A loose question made the tool answer yes for all 8
   test companies, and it mixed up two companies called Notion.
6. **Tell the user what a step costs before you run it,** and wait for a yes. Measured: LinkedIn
   pull about $0.004 a company on Apify. Tavily 1 credit a search. Serper 1 credit a search.
   Exa about $0.005 an answer. Parallel is priced per run by processor.
7. For more than 50 companies, run the first 5 and show the result before the rest.

## Steps

### 0. Check the setup (no spending)

```bash
for k in APIFY_TOKEN PARALLEL_API_KEY TAVILY_API_KEY EXA_API_KEY SERPER_API_KEY; do
  if grep -q "^$k=.\+" .env 2>/dev/null || [ -n "$(printenv $k)" ]; then echo "$k: set"; else echo "$k: missing"; fi
done
```

APIFY_TOKEN is needed only to pull LinkedIn text (step 3), so not when `work/companies.csv`
already exists. At least one research key is needed for step 5. If a key you need is missing, tell
the user which sign-up page to use (README, "Setup") and stop.

### 1. The question

Ask the user for the yes/no question. Open `brief.md` and edit only the marked block:

- `QUESTION:` the question you will answer from each company's LinkedIn text.
- `RESEARCH_QUESTION:` the sharp version for the research tool. Keep `{name}` and `{website}`.
  Say what counts as no. Ask for "yes, no or cannot tell first, then one sentence of evidence".
- `SEARCH_QUERY:` a short Google query with `{name}` and `{website}` (used only by Serper).

Also change the "Who we are" line. Show the three lines to the user and get a yes.

### 2. The companies

The user gives LinkedIn company pages. Write `work/companies.txt`, one per line:

    https://www.linkedin.com/company/plaid-/ | Plaid | plaid.com

The name and website after the bars are what the USER expects. They are how step 3 catches a wrong
company. If the user has only company names, ask for the LinkedIn addresses. Do not guess them.

### 3. LinkedIn descriptions

If `work/companies.csv` already exists for these companies, use it and skip to step 4. Pulling
again costs money.

```bash
python3 scripts/01_linkedin.py
```

Writes `work/linkedin_raw.json` (the complete answer, keep it) and `work/companies.csv`.
Show the flagged rows. `website_mismatch` or `name_mismatch` means the address may point at the
wrong company: ask the user to fix the address in `companies.txt` and re-run only if they agree
(each run costs money). `short_description` means there is little text to judge.
To replay a saved pull for free: `python3 scripts/01_linkedin.py --raw work/linkedin_raw.json`.

### 4. Judge from the LinkedIn text (you do this)

Read `brief.md` and `scripts/02_judge.md`. Read `work/companies.csv` 20 companies at a time. For
each company return id, verdict (yes / no / cannot tell), reason, quote, confidence. Write
`work/judged.csv` with the header `id,name,verdict,reason,quote,confidence` (use a CSV writer so
quotes inside text are escaped). Then check your quotes:

```bash
python3 scripts/02_judge.py --check work/judged.csv
```

Any yes or no whose quote is not in the company's text becomes "cannot tell". Report the counts.

If the user wants it without you reading, `python3 scripts/02_judge.py` does the same step from
the terminal with their Claude Code login.

### 5. Research the "cannot tell" rows

Pick the tool from the keys that are set. Parallel gives the cleanest answers, with sources.
Exa and Tavily are quick and cheap. Serper returns only Google results.

```bash
python3 scripts/03_research_parallel.py     # PARALLEL_API_KEY. Runs rows in parallel, about 45 s for 7.
python3 scripts/03_research_exa.py          # EXA_API_KEY
python3 scripts/03_research_tavily.py       # TAVILY_API_KEY
python3 scripts/03_search_serper.py         # SERPER_API_KEY
```

Each one does only the "cannot tell" rows. `--ids 3,5` picks rows, `--all` does every company.
If the user wants a second opinion, run two tools. The merge step shows where they disagree.

### 6. Read the answers that are not a clean yes or no

Tavily often answers in a sentence. Serper gives only Google results. Read them yourself, following
`scripts/03_review.md`, and write `work/research_review.csv` with the header
`id,tool,verdict,reason`. Or run `python3 scripts/02_judge.py --review`. Skip this step if every
research answer was already a clean yes or no.

### 7. Merge

```bash
python3 scripts/04_merge.py
```

Writes `work/results.csv`. Tell the user: the counts, how many rows came from the LinkedIn text and
how many from research, and every row with `needs_review = yes` and why (see the `check` column).
Offer to show the yes rows with their quotes.

## What to say in the final message

- The three counts (yes, no, cannot tell) and where each came from.
- Rows to look at first: needs_review, and any "cannot tell" left.
- What was spent, from the numbers the scripts printed.
- That a "no" from research rests on web pages, a "no" from LinkedIn rests on the company's own
  words, and the results file says which.
