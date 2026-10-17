# What was actually checked

These are development smoke tests on fixed public project questions, not an
untouched benchmark or a claim of finance-answer accuracy.

## Environment and reproducibility

Run date: 17 October 2026. Apple M2, 8 GB unified memory, Python 3.12.
The checked-in JSON reports include the actual package versions, model revisions,
prompt template/hash, corpus hash, source text, generated text and elapsed times.
MPS uses bfloat16; CPU uses float32. No quantisation, fine-tuning or hosted API.
Other operating systems and hardware combinations were not tested in this run.

The first FP16 accelerator experiment produced invalid output with the 1.5B model.
It is not a valid model-quality comparison. The released runtime uses BF16 and
checks logits for numeric failure. Earlier development logs remain local, outside
the public release; both final reports below use the same prompt and corpus.

## Retrieval — separate from answer quality

Both [small-final-bf16.json](small-final-bf16.json) and
[larger-final-bf16.json](larger-final-bf16.json) contain the same retrieval run:

| Check | Result |
|---|---:|
| Reference evidence hit@3, MiniLM + FAISS | 40 / 41 |
| Reference evidence hit@3, lexical baseline | 40 / 41 |
| Wrong-version passages retrieved | 0 |
| Token-bounded passages | 92 |

The baseline uses the same token passages, version filtering and source-section
diversity. A hit requires an expected document/heading among three sections.
The local assistant document replaces the website's old provider notes in the
reference mapping. Both methods miss the broad beginner “where should I start?”
reference. This does **not** demonstrate semantic retrieval outperforming keywords.
It also does not prove the best source is ranked first, the relevant sentence is
in an overlapping subchunk, or that the generator used the evidence correctly.

## Generation — format success is not factual success

Each final run contains 12 actual Qwen calls plus four local boundary responses.
The boundary replies cover live prices, unverifiable personal contribution,
credential requests and guaranteed investment returns; they make no LLM call.

| Model | Valid source-labelled response structure | Explicit source-only fallback |
|---|---:|---:|
| Qwen 0.5B | 3 / 12 | 9 / 12 |
| Qwen 1.5B | 11 / 12 | 1 / 12 |

These counts are **schema/citation-ID results, not accuracy**. The 1.5B model is
the default because it follows the response format more reliably, not because
its finance explanations are proven reliable. A valid JSON answer can be wrong.

Manual inspection of the actual 1.5B responses found:

- Share, borrowing, discounting and billion-versus-million answers were broadly
  consistent with the notes. The review's Ridge/baseline numbers were reproduced.
- The **6.5 versus 5.5 CAPM answer was incorrect/inadequate**: 6.5% is the saved
  risk-free proxy; 5.5% is the assumed equity risk premium. They are not two values
  of the same premium. The model's cited source states this more clearly than its answer.
- The NPV response was generic, omitted the requested calculation and selected an
  unhelpful source label. The recorded NPV is ₹70.543213 crore; inflow PV is
  ₹836.983216 crore. The chatbot must not be relied on to reconstruct this arithmetic.
- Collar, walk-forward, Sharpe and RAG responses omitted parts of the questions
  or were too terse. In particular, the collar answer did not explain the capped
  upside, and expanding the RAG acronym did not explain the pipeline.
- The WACC call reached a limit and was correctly displayed as a source-only
  fallback. That is not a successful generated explanation.

No aggregate “LLM accuracy” is reported: a short, subjective review on these
known questions is not a general accuracy measurement. This is a **working RAG
learning prototype, not an independently reliable finance tutor**. Always read
the source notes, especially for numbers, units and interview claims.

## Software and release checks

- 14 local chatbot tests: routing, prompt evidence, malformed/missing/unknown
  citations, output/time caps, version validation, follow-ups and escaped source HTML.
- 40 pre-existing dashboard/knowledge-base/assistant tests passed on an export
  of the staged release, without the unrelated local finance-review edits.
- Dependency consistency and static checks passed. These checks do not grade
  the natural-language finance explanations.
- `python -m local_chatbot.check_offline` produced a real sourced share answer
  with Python `socket.connect` blocked and **zero connection attempts**. This is
  a focused runtime smoke check, not a complete OS-level network audit.

## Re-run

From the repository root, after model preparation:

```bash
python -m local_chatbot.evaluate --model small --output local_chatbot/evaluation/private_runs/my-small.json
python -m local_chatbot.evaluate --model larger --output local_chatbot/evaluation/private_runs/my-larger.json
```

Run one model process at a time on a small laptop. Compare response text and
source support, not just format-pass counts. Timings vary with memory pressure,
device, input length and model load; the first response includes loading. Memory
snapshots in the reports are end-of-run readings, not peak RAM or a guarantee.

Useful next experiments are a separately evaluated stronger/quantised model,
better context selection, and validated calculator/fact tools for exact numbers.
Do not claim these are implemented or quietly tune the finance backtest score.
