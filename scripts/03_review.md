# Reading step for research answers (Claude Code does this itself)

Some research tools do not give a clean yes or no. Tavily writes a sentence. Serper gives Google
results and nothing else. This step reads what they returned and decides.

You get a list of items. Each item has an id, the tool, the exact question that was asked about
that company, and the text the tool returned (an answer, snippets, or both).

Rules:

- Answer the question that was asked, exactly as worded. Read what "yes" means in that question.
- Use only the text given. Do not use what you remember about the company.
- yes or no only when the text supports it. Otherwise "cannot tell".
- A search result about a different company with a similar name is not evidence. Ignore it.
- Give one short reason. Name the page you relied on if the text shows its address.
- Return one entry for every item, in the same order.

Return only a JSON array. No words before it or after it. Each entry has exactly these keys:

    {"id": "1", "tool": "tavily", "verdict": "no", "reason": "one short sentence"}

verdict is one of: yes, no, cannot tell.

## The items

{{ITEMS}}
