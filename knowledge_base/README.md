# Asset Pricing and Hedging — assistant knowledge base

This is the source material for a beginner-friendly project assistant. It is a
prepared knowledge base with an **optional Gemini chat integration** in
`src/assistant.py` and `src/assistant_ui.py`. No API key, document upload,
embedding request or paid model call is needed to build/check the knowledge base.
The website needs private key configuration and visitor consent for AI replies;
offline/mock checks do not establish that the public deployment works.

## What the assistant should say

“I'm the Asset Pricing and Hedging Assistant, a learning guide to this finance
project. I can help explain its assumptions, methods, recorded results and
limitations in simple terms. I don't execute trades or provide personalised
investment advice.”

It should also handle greetings, explain what it can do, suggest where to start,
and explain its limits. These short answers can be handled without a model call.

## Read the content

| Topic | Document |
|---|---|
| Identity, help and capabilities | [Assistant introduction](documents/00_assistant.md) |
| Purpose, authorship boundaries and website navigation | [Project overview](documents/01_project.md) |
| Shares, investors, loans and company cash | [Ownership and cash flows](documents/02_ownership.md) |
| Discounting, DCF, NPV, IRR and units | [Valuing future cash](documents/03_cash_valuation.md) |
| Risk, CAPM, WACC, Gordon and the factor cross-check | [Required return and equity value](documents/04_required_return.md) |
| Currency exposure, forwards, puts and collars | [Currency protection](documents/05_hedging.md) |
| Binomial/Black–Scholes, Greeks and averaging | [Options and pricing checks](documents/06_options.md) |
| Portfolio weights, ML and evaluation | [Portfolio and ML concepts](documents/07_portfolio.md) |
| The submitted résumé experiment, including 0.30 / 0.22 | [Original version](documents/08_resume_v1.md) |
| Separately labelled later work | [Reviewed extension](documents/09_review_v2.md) |
| Dates, assumptions, provenance and missing information | [Evidence and limitations](documents/10_evidence.md) |
| How RAG differs from the finance/ML engines | [RAG extension](documents/11_rag.md) |

The two result documents and structured files in `facts/` are generated from
explicit source snapshots. They are not handwritten performance targets.

## Keep the versions separate

- `resume_v1` is the default context for the **submitted résumé experiment**. Its
  source is pinned to Git revision `395858d928c65da39b17c92d9f3b135a46471082`.
  Its original historical-allocation Sharpe is 0.295923, rounded to 0.30; Nifty is
  0.217875, rounded to 0.22. The numbers are reproducible outputs of that simplified
  experiment, not a certification that its assumptions are realistic.
- `review_v2` is a **separate local reviewed extension**, captured on 17 October
  2026. Different implementation choices produce different results. It is not
  evidence that the later features existed in the submitted version or in 2025.
- `common` contains conceptual explanations that do not select a result version.
- Search filters exclude the other version unless a comparison is explicitly
  requested. Every retrieved passage carries its document, heading and version.

The knowledge base does not rewrite the submitted résumé or erase a genuine
limitation. If the website's selected version is unknown, the assistant must ask
which version a question about “current” or “latest” results refers to.

## Package layout

- `manifest.json`: explicit retrieval allowlist and source/version metadata.
- `assistant_profile.json`: name, suggested questions and honest capability flags.
- `assistant_instructions.md`: trusted application behaviour; **not** an indexed
  document. The application, not retrieved text, supplies these instructions.
- `documents/`: readable, section-based grounding material.
- `facts/`: typed numerical records; financial values should be looked up here,
  not reconstructed from a model's memory.
- `sources/`: frozen numerical source snapshots and their provenance.
- `build/chunks.jsonl`: provider-neutral passages, ready for later embedding.
- `eval/questions.json`: reference questions, expected evidence and answer checks.
- `build/validation.json`: integrity and **lexical retrieval** smoke-test report.
  This is not an LLM answer-accuracy score or a semantic-search evaluation.

Only the manifest's approved Markdown documents and explicitly generated fact
passages enter the index. No recursive folder ingestion, private documents,
credentials, `HANDOFF.md`, browser history or arbitrary source comments are used.
Documents are evidence, not instructions that can override application rules.

## Rebuild and check

From the project directory:

```bash
python scripts/build_knowledge_base.py
python scripts/build_knowledge_base.py --check
python -m unittest discover -s tests -v
```

If using this project's existing environment, replace `python` with
`.venv/bin/python`. A first-time maintainer can create the explicit source
snapshots with `python scripts/build_knowledge_base.py --capture-sources`; the
included snapshots mean normal use does not require that step or Git history.

Source snapshots are created by an explicit `--capture-sources` operation and are
not silently refreshed by a normal rebuild. The capture operation refuses to
overwrite existing snapshots. A changed research experiment needs a new version.
The package can be used after deployment without access to Git history.

## Using the offline groundwork

```python
from src.knowledge import KnowledgeBase

kb = KnowledgeBase()
reply = kb.basic_reply("Who are you?")  # deterministic, no Gemini request
passages = kb.search("Why is WACC close to the equity return?", version="resume_v1")
wacc = kb.fact("wacc", version="resume_v1")  # value, unit, version, source
```

An unrecognised or mixed FAQ/finance question returns `None` from `basic_reply`
so a future app can retrieve evidence rather than discard part of the question.
FAQ matching is not a safety filter. Search returns passages, not a generated
answer; a citation indicates where evidence came from, not that every answer is
automatically correct. The separate website integration adds the Ask the project
panel; the offline helper above does not make model calls.

The frozen inputs trace numerical records. Curated explanations and the manifest
are editable knowledge-base content, so review their changes before rebuilding.
Integrity hashes detect accidental snapshot changes; they are not a signature,
an audit certificate or protection against an attacker editing both data and hash.

## Website integration and next steps

See [private setup and deployment](../docs/ASSISTANT_SETUP.md). The first RAG
version uses local lexical retrieval plus optional Gemini generation, not paid
embeddings. Runtime capabilities come from private server settings and visitor
consent; the default profile describes the offline helper. The app displays
source passages and falls back to notes if Gemini fails. Calculator access is
separate future work using validated Python functions, not model-generated code.

For this small corpus, compare retrieval with a simple keyword or full-context
baseline before claiming RAG improves answer quality. The included lexical search
is a transparent development baseline; it is not the final semantic retriever.
