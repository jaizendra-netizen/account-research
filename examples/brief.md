# Account research brief

<!-- ===== EDIT ONLY THIS BLOCK. It is the one place the question lives. ===== -->
<!-- Keep each of the three lines below on ONE line. Keep the labels (QUESTION: and so on). -->

QUESTION: Does this company sell software to banks, insurers or lenders?
RESEARCH_QUESTION: About the company {name} (website {website}): is its main product built specifically for banks, insurers or lenders? A general tool that some banks also use counts as no. Answer yes, no or cannot tell first, then one sentence of evidence.
SEARCH_QUERY: {name} {website} customers banks insurers lenders

<!-- ===== END OF EDIT BLOCK ===== -->

How to write the three lines:

- QUESTION is what Claude answers from each company's own LinkedIn text. One yes/no question. Nothing else.
- RESEARCH_QUESTION is the same question made sharper for a web research tool, which has no
  text of ours to read. It must carry the company name, the website, what counts as "no", and
  the order of the answer. {name} and {website} are filled in for each company.
- SEARCH_QUERY is only used by the Google search script (03_search_serper.py).

## Who we are

We sell software to financial institutions. (EDIT: one line about what you sell.)

## Rules

1. Judge only from the company's own text given with each company. Never use an industry label.
2. If the text does not answer the question, say "cannot tell". Do not guess.
3. Quote the exact words that support your verdict. Copy them letter for letter.
4. "Serves banks" and "is a bank" are different things. We want companies that serve them.

## For each company return

- id
- verdict: yes | no | cannot tell
- reason: one or two sentences
- quote: the supporting words, copied exactly
- confidence: high | medium | low
