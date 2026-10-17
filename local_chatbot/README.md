# Local Finance RAG — learn the complete pipeline

A downloadable, on-device chatbot for the **Asset Pricing and Hedging** project.
Ask a finance question, read the answer, then inspect the notes used to produce it.
No Gemini key, paid API, Hugging Face account or cloud deployment is required.

This is a separate learning app. It does **not** replace or change the Streamlit
dashboard, its finance calculations, or its saved results.

## What you will learn

```text
Approved finance notes → token-bounded passages → MiniLM embeddings → FAISS index
                                                                          ↑
Question → MiniLM question embedding → search selected version ────────────┘
                                           ↓
                       relevant passages + question → Qwen → answer + sources
```

| Component | Actual implementation |
|---|---|
| Interface | Gradio, bound to your laptop's loopback address |
| Knowledge | Curated project Markdown, source metadata, separate research versions |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2`, 384 dimensions |
| Retrieval | Normalised vectors; FAISS `IndexFlatIP` exact cosine search |
| Generation | `Qwen/Qwen2.5-1.5B-Instruct` by default; optional 0.5B experiment |
| Visibility | Retrieved passages, scores, evidence prompt, timings and raw model text |
| Framework | Explicit Python functions; no orchestration framework required |

The model IDs and immutable download revisions are in [config.py](config.py).
Model weights, generated indexes and virtual environments are **not** in GitHub.

## 1. Download the project

Use GitHub **Code → Download ZIP**, extract it, and open a terminal inside the
extracted `asset-pricing-and-hedging-main` folder. Keep the whole repository:
the chatbot reuses `src/knowledge.py` and `knowledge_base/`.

Or, with Git installed:

```bash
git clone https://github.com/arathii23/asset-pricing-and-hedging.git
cd asset-pricing-and-hedging
```

All commands below run from this **repository root**, not inside `local_chatbot`.

## 2. Create a separate Python environment

Use **64-bit Python 3.12**. Do not reuse the dashboard environment. Installing
the root `requirements.txt` is not necessary for this chatbot.

macOS / Linux:

```bash
python3.12 -m venv local_chatbot/.venv
source local_chatbot/.venv/bin/activate
python -m pip install -r local_chatbot/requirements-tested.txt
```

Windows PowerShell:

```powershell
py -3.12 -m venv local_chatbot/.venv
.\local_chatbot\.venv\Scripts\python.exe -m pip install -r local_chatbot/requirements-tested.txt
```

Windows commands below can use
`.\local_chatbot\.venv\Scripts\python.exe` wherever you see `python`. This avoids
needing to change PowerShell's activation policy.

First installation needs internet access and several GB of free disk space for
libraries, model weights and caches. Default Qwen weights alone are about 3 GB.
Prefer **16 GB RAM for CPU use**; the default was also tested on an 8 GB Apple M2
using MPS acceleration. This is not a universal memory guarantee. Close heavy
apps and run one model process at a time. CPU uses float32; MPS uses bfloat16 to
avoid the FP16 numeric failures found during development. MPS needs a compatible
macOS/PyTorch runtime; CUDA acceleration needs bfloat16 support. Otherwise use
CPU. No quantisation is implemented. Windows/Linux instructions are portability
guidance, not a claim that every hardware combination was tested.

`requirements-tested.txt` pins the tested direct versions, not every transitive
dependency. `requirements.txt` is the broader bounded variant for development.

## 3. Prepare the models and search index — once

```bash
python -m local_chatbot.prepare
```

This explicitly downloads pinned public MiniLM and Qwen weights, loads only
SafeTensors weights with remote Python code disabled, embeds the approved notes
and builds local search artifacts. Large downloads can take several minutes.
It sends ordinary download requests, **not your questions**. No login or key.

After preparation, the app uses local files only. To rebuild the index after
editing approved notes without making download requests:

```bash
python -m local_chatbot.prepare --offline
```

## 4. Start the chatbot

```bash
python -m local_chatbot.app
```

Open **http://127.0.0.1:7860** in your browser. Keep the terminal open.
Press Ctrl+C in that terminal to stop the app. To start it again later, activate
the same environment and run this command; you do not need to download again.

The interface has three views:

- **Ask the project:** choose a research version and ask one question at a time.
- **Learning view:** inspect the retrieval query, notes, scores and exact evidence
  prompt. Raw model output is explicitly unverified, including rejected answers.
- **How RAG works:** a step-by-step explanation of the components.

Try these in order:

1. “Who are you?” — notice the labelled FAQ route; no LLM was called.
2. “What is a share?” — inspect a real retrieval + generation response.
3. “Why does a company borrow if it already has money?”
4. “Why discount future cash?”
5. “What is the difference between 6.5 and 5.5 in CAPM?”
6. “What do 0.30 Sharpe and 0.22 Nifty mean?” — check the original version.
7. “What is Infosys trading at right now?” — the app must not invent live data.

First finance question includes model load time. Questions are processed one at
a time to limit memory use. Short follow-ups can reuse the previous **user
question**, not the model's previous answer, as topic context. Changing version
clears the conversation.

For a plain terminal response:

```bash
python -m local_chatbot.chat "What is a share?"
python -m local_chatbot.chat "Why is WACC close to 10.96%?" --trace
```

## Optional: inspect a lighter model's limitations

```bash
python -m local_chatbot.prepare --model small
python -m local_chatbot.app --model small
```

This downloads `Qwen/Qwen2.5-0.5B-Instruct` (about 1 GB of weights). It is a
lower-memory **experiment, not recommended for financial figures**. Earlier runs
made serious unit/grounding errors and often ignored citations. Compare actual
responses, not just model size or fluent wording. The 1.5B default is still not a
promise of correct answers. Only run one model process at a time on a small laptop.

## Understand the implementation

Read [LEARNING_GUIDE.md](LEARNING_GUIDE.md), then these files in order:

1. [config.py](config.py): model revisions, paths and explicit budgets.
2. [corpus.py](corpus.py): allowlisted notes, source/version metadata and chunking.
3. [retriever.py](retriever.py): embedding normalisation and FAISS search.
4. [generator.py](generator.py): local Qwen loading and deterministic inference.
5. [pipeline.py](pipeline.py): FAQ routing, evidence packing, generation and checks.
6. [app.py](app.py): Gradio interface and session-only conversation state.
7. [evaluate.py](evaluate.py): retrieval comparison and actual-model smoke runs.

[prompts.py](prompts.py) keeps the public instructions and one fictional
formatting example separate. Qwen returns JSON containing `answer` and
`source_ids`; Python validates it and displays the source labels. This is
structured output with validation, **not constrained decoding or fine-tuning**.
Bad JSON is rejected rather than repaired by guessing. The learning view shows
both the template and the question/evidence, so the model input is inspectable.

Long sections are split by MiniLM token offsets, with headings included in the
224-token input budget and 32 tokens of overlap. This avoids MiniLM's default
256-wordpiece truncation. Top-three retrieval is diversified by source section;
it can still miss a relevant part of a long section. Search is filtered by version
**before** nearest-neighbour selection. Common explanatory notes can explicitly
discuss both versions; metadata isolation is not a guarantee against semantic
confusion inside an answer.

The website's old assistant/provider notes describe its Gemini integration.
This local app replaces those two documents in its own corpus with
[knowledge.md](knowledge.md), without changing the website's knowledge base.
It reuses finance explanations and recorded facts, not the entire working folder.
No private handoff, keys, personal files or arbitrary uploads are indexed.

## Check it honestly

Fast checks, without downloading or running models:

```bash
python -m unittest discover -s local_chatbot/tests -v
```

After preparation, run real-model checks:

```bash
python -m local_chatbot.evaluate --retrieval-only
python -m local_chatbot.evaluate
python -m local_chatbot.check_offline
```

Reports go to `local_chatbot/evaluation/latest.json` and contain the fixed public
reference questions, source passages and real responses, not private chat.
Do not publish arbitrary personal test questions or logs. See
[evaluation/README.md](evaluation/README.md) for the checked-in run and limitations.

**Hit@3 is not LLM accuracy.** It checks whether expected evidence appears among
three retrieved sections. The lexical baseline uses the same token passages,
version filter and section diversity. The reference cases predate this semantic
implementation but are small, project-authored and not an untouched benchmark.
Manually verify answer support, units, abstention and completeness separately.
The default still made an incorrect/inadequate CAPM explanation and omitted
parts of other questions in the published run. This is a working learning
prototype, **not an independently reliable finance tutor**. Read the evaluation
notes before using it to prepare interview answers.

## Boundaries and known limitations

- Small Qwen models can hallucinate, omit caveats or misunderstand calculations,
  even with correct retrieval. Check the source text before using an answer.
- Similarity scores and the 0.30 no-evidence threshold are heuristics, not
  probabilities or calibrated confidence. Relevant-looking wrong answers remain
  possible. Citation validation checks IDs, **not factual entailment**.
- Unknown/missing source IDs, invalid JSON or an output/time cap cause a labelled source-only
  fallback. A model error is not reported as a successful generated answer.
- This app does not execute a calculator, browse, fetch live prices, trade,
  guarantee profits, fine-tune models or prove historical outperformance.
- The original experiment and later review have different results. The 2026 data
  does not verify a 2025 résumé chronology or anyone's personal contribution.
- Finance arithmetic should come from validated Python calculations/recorded
  results, not be invented by an LLM. RAG does not repair the original finance model.
- Input/source instructions are untrusted. Prompt rules and simple scope checks
  are not a complete prompt-injection defence. No LLM tools execute actions.
- Chat is held in process memory for the browser session, capped at eight turns,
  not permanently saved. Browser state/network access must still be secured.

The default server listens only on `127.0.0.1`, with no public sharing tunnel.
Do not expose it to the internet or set `share=True` without a separate security
and authentication review. This is a local learning demo, not a production service.
Model downloads are the only intended external model requests. Gradio/Hugging
Face telemetry is disabled in this process. Model loading uses local-only mode.

## Troubleshooting

| Problem | Action |
|---|---|
| `No module named local_chatbot` | Run from the repository root; keep `src/` and `knowledge_base/` beside the chatbot folder. |
| Models/index missing | Run preparation once with internet. Do not move/delete the ignored model cache afterwards. |
| Stale index | Run `python -m local_chatbot.prepare --offline`. |
| Memory error or MPS failure | Close heavy apps; try `--device cpu` with sufficient RAM. The optional `--model small` uses less RAM but has worse answer quality. |
| Slow generation | CPU can be slow; use shorter questions. The output budget and approximate 90-second generation deadline are bounded, not hard kernel timeouts. |
| Port occupied | Add `--port 7861` and open that port. |
| SSL certificate error | Repair your Python/OS certificate installation or organisation's approved certificate setup. Do not disable TLS verification. |
| No compatible FAISS/PyTorch wheel | Use 64-bit Python 3.12 on a supported OS; do not install a random wheel from an untrusted site. |
| Package-version problem | Start a clean chatbot environment. See the tested direct versions; other OS/CPU combinations require verification. |
| Source-only response | Read the notes and inspect raw model text. Do not count it as a successful AI answer. |

## Licences and attribution

New code and documentation under `local_chatbot/` are MIT-licensed; see
[LICENSE](LICENSE). This grant does **not** relicense the existing finance code,
knowledge base, source snapshots, datasets or third-party models. Their existing
terms remain unchanged; check them before redistribution beyond downloading this
public project for learning. Model weights are downloaded from their publishers,
not redistributed in this repository. Model cards specify Apache-2.0 for the
chosen MiniLM and Qwen models. See [THIRD_PARTY.md](THIRD_PARTY.md).
