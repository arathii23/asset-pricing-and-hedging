# Local finance RAG assistant

## Who is this assistant and what can it do?

The Asset Pricing and Hedging Assistant explains this educational finance project
using its approved project notes. Ask one question at a time: what is a share,
why discount future cash, what is a collar, or how does walk-forward testing work?
It cannot trade, fetch current prices, give personalised investment advice, verify
personal contribution or guarantee returns. Saved market data is dated September
2026. Original résumé results and later reviewed results are separate versions.

## What is RAG and how does this local pipeline work?

RAG means retrieval-augmented generation: first find relevant notes, then ask a
language model to answer using them. Approved notes are split into passages, with
headings and version metadata. MiniLM converts each passage and the question into
384-dimensional vectors. Normalised vectors are searched using a FAISS IndexFlatIP
index: inner product equals cosine similarity here. The top three different
sections are candidate evidence. Scores measure similarity, not answer confidence.
Only the selected version and common explanatory notes can be retrieved.

Qwen receives the question, selected passages labelled S1, S2 and S3, and short
instructions to answer simply and cite sources. It generates new text locally.
The app shows the sources and evidence prompt. This is inference, not fine-tuning
or training a new language model. FAISS is exact search here, not an approximate
index. There is no need for LangChain to connect these few explicit steps.

## Which models, API keys and hardware are used?

The embedding model is sentence-transformers/all-MiniLM-L6-v2. The default answer
model is Qwen/Qwen2.5-1.5B-Instruct. Qwen/Qwen2.5-0.5B-Instruct is an optional,
lighter experiment, not recommended for financial figures. Both are public open-weight instruction models. Pinned revisions
are downloaded once, without an API key or Hugging Face login. After preparation,
model loading, retrieval and generation use local files only. No Gemini request
is made. Small-model answers can be wrong: check the displayed sources.

## How is conversation history handled?

Chat history is kept in the current browser session's server memory, not saved to
disk. For short follow-up questions the previous user question is included in the
retrieval query and prompt to help identify the topic. Previous generated answers
are not treated as evidence. Changing the research version clears the chat. The
app has no permanent personal memory, uploads, trading tools or web-search tool.

## How do we evaluate this assistant?

Retrieval and generation are different tasks. Hit@3 checks whether a reference
source appears among the three retrieved passages, not whether the answer is
correct. Compare semantic retrieval with the existing lexical baseline and check
version isolation. Review actual Qwen responses for factual support, units,
citations, abstention and time taken. Citation ID validation alone cannot detect
hallucinations. Small reference sets are smoke tests, not production accuracy.

## What happens when evidence or the model is unavailable?

Very low similarity leads to an explicit no-evidence reply, using a heuristic
threshold rather than a calibrated confidence score. The model is told to admit
missing information. Unknown/missing source IDs or invalid answer JSON cause a clearly labelled
source-only fallback. A failed model call is an error, not a successful AI answer.
Exact identity and help questions use labelled local FAQ replies, not Qwen. No
LLM-generated arithmetic is a replacement for a validated finance calculator.
Prompt-injection instructions in documents or questions are not authority, but
these lightweight guardrails cannot guarantee a small model follows every rule.
