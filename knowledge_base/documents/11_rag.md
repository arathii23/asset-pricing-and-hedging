# The finance assistant and RAG

## What is RAG in simple terms?

Retrieval-augmented generation means finding relevant project passages before
asking a language model to explain an answer. Think of an open-book assistant:
it looks up the appropriate notes, then answers with references. It is not
training a new foundation model on this project, and it does not make the finance
methods or historical returns more accurate by itself.

## What material is approved for the assistant?

The manifest explicitly lists curated explanations, original versus later method
notes, typed numerical facts and their frozen provenance. It includes identity,
navigation, beginner finance and interview limitations. It does not ingest the
whole working folder, private files, HANDOFF.md, API keys, private chats or
arbitrary comments. Trusted application instructions stay outside the searchable
documents. Retrieved material is evidence, not permission to execute instructions.

## What is implemented now and what still needs connection?

The package contains readable notes, heading-based passages, version metadata,
fact lookup, local lexical search, basic FAQ responses and reference tests. The
Ask the project page connects this retrieval to optional Gemini generation using
a server-side key and visitor consent. Without the key or consent, it displays
relevant source passages directly; basic identity/help needs no model call.
No semantic embeddings, live market feed, calculator tool or trading connection
is implemented. Code and offline/mock tests do not verify a live deployment or
Gemini answer quality; the actual running application must report its status.

## How would a question travel through the finished assistant?

The application supplies the selected research version and enabled capabilities.
Basic identity/help receives an immediate local response. A project question
retrieves up to four approved passages for that version plus relevant structured
saved values when applicable. With consent and a configured key, Gemini receives
that evidence, trusted instructions and a few recent same-version messages.
The app validates the response structure and source IDs before showing an AI
answer; a bad response falls back to notes. Those checks cannot prove that each
claim is supported. An active-scenario calculator remains a separate future
validated Python tool, not arithmetic invented by the language model.

Embeddings represent meaning numerically for retrieval; Google documents a Gemini
embedding interface for tasks such as semantic search. Model names, availability,
quotas, permissions and pricing must be checked when integrating rather than
assumed from this preparation: [Google — Embeddings](https://ai.google.dev/gemini-api/docs/embeddings).

## Will the owner need to provide a Gemini API key? Will visitors need one?

The optional server-side Gemini integration needs an authorised key for the
configured project. The app owner can supply it privately through Streamlit
Secrets; visitors need not each enter their own key in this design. Do not paste
the key into a chat, commit it to Git or expose it to the browser. Preparing this
knowledge base requires no key and makes no paid model requests.

[Google — API key security](https://ai.google.dev/gemini-api/docs/api-key) explains
keeping keys confidential and server-side. [Streamlit — Community Cloud secrets](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management)
explains private deployment configuration. The owner's quota/billing applies to
requests made with their key. The app limits question/history length, caps output,
does not automatically retry, and applies session/cooldown limits plus a
best-effort per-running-server daily allowance. The allowance resets after a
process restart and is not coordinated across replicas: it is NOT a strict
billing cap. Provider-side quotas or stronger shared enforcement are needed
before a high-traffic public launch.

## What privacy and cost boundaries should a public chatbot have?

When Gemini is enabled, submitted questions and selected passages will be sent to
the configured external provider. Do not claim all processing is local or ask
for confidential company records or personal financial details. Applicable
provider terms and the project's billing configuration must be reviewed before
launch. Keep only the necessary conversation context, limit question length and
request frequency, and handle unavailable service without exposing secrets.
No permanent personal memory is implemented in this package.

## How will we know the assistant is useful rather than just fluent?

Use reference questions covering basic finance, identity, calculations, source
citations, missing information, version separation and unsafe requests. Check
retrieval separately from final answers: correct evidence in the top passages
does not prove that a model used it correctly. Compare a simple keyword or
full-context baseline against semantic retrieval for this small corpus. Then
check factual correctness, citation support, abstention, latency and cost with
actual model responses. Current lexical smoke tests are not LLM answer accuracy.

## What can be claimed on a future AI/ML résumé?

Once integrated and tested, describe the actual retrieval method, Gemini-based
generation, source citations, evaluation and deployment. Finance portfolio ML
and RAG answer generation are different components. Do not say a foundation model
was trained, a semantic system was deployed, hallucinations were eliminated or
an accuracy score was achieved merely because a knowledge base was prepared.
The implementation now includes version-filtered lexical RAG, optional Gemini
generation, a Streamlit chat interface and offline/mock checks. Public deployment
and live-model quality must be verified separately. Do not claim semantic search,
measured model accuracy or a production-grade billing/security boundary.
