# Judging step (Claude Code does this itself)

You are given a brief and a batch of companies. Each company has an id, a name and the text
the company wrote about itself on LinkedIn. Answer the brief's question for every company.

Rules that matter more than anything else:

- Use only the text given. Do not use what you remember about the company.
- If the text does not answer the question, the verdict is "cannot tell".
- Every "yes" and every "no" needs a quote: the exact words from the text, copied letter for
  letter. If you cannot quote, the verdict is "cannot tell".
- A "no" must be earned. It needs text that shows the company sells to someone else, such as a
  named industry or customer group. A general tool whose text names no customers (for example
  "a work management platform") is "cannot tell", not "no". Silence is not a no.
- Return one entry for every company in the batch, in the same order.

Return only a JSON array. No words before it or after it. Each entry has exactly these keys:

    {"id": "1", "verdict": "yes", "reason": "one or two sentences", "quote": "exact words", "confidence": "high"}

verdict is one of: yes, no, cannot tell. confidence is one of: high, medium, low.

## The brief

{{BRIEF}}

## The companies

{{COMPANIES}}
