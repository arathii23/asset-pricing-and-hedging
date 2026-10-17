# Project assistant: private setup and deployment

The Ask the project page explains the saved finance project using a curated,
versioned knowledge base. The first RAG implementation uses local lexical
retrieval and optional Gemini generation. It does not use semantic embeddings or
a paid vector database. No new Python dependencies are required.

## Enter the key privately

In Streamlit Community Cloud, open this app's settings, choose Secrets and enter:

```toml
GEMINI_API_KEY = "YOUR_ACTUAL_GEMINI_API_KEY"
```

Replace the placeholder privately, retain the quotes and save. Keep any existing
real secret entries. Never paste the key in chat, a screenshot, a source file or
GitHub. Saving a key does not deploy code or prove the key/model is authorised.
The updated app must also be deployed before the page appears.

Optional owner settings:

```toml
GEMINI_MODEL = "gemini-3.8-flash"
CHAT_ENABLED = true
CHAT_DAILY_LIMIT = 50
```

The default model was checked against Google's official model catalogue on
17 October 2026. Availability, permissions, quota and billing depend on the
owner's project. Set `CHAT_ENABLED = false` to disable model requests while
leaving the local notes/FAQ usable. No guarantee of a free tier is made.

Locally, put the same settings in `.streamlit/secrets.toml` (Git-ignored), or
provide the named environment variables. `.streamlit/secrets.example.toml` is a
tracked placeholder example only. Do not put a real key in that example.

## Try the assistant

1. Open Ask the project from the sidebar or the overview button.
2. Select the original résumé experiment or later reviewed extension. The page
   identifies when this differs from the dashboard charts. Changing the selection
   clears conversation context to avoid mixing experiments.
3. Ask “Who are you?” or “What can you do?” These basic answers stay local.
4. Without AI enabled, ask “What is a share?” to see the matching source passage.
5. Tick Use Gemini for explanations. This consents to sending the question, a few
   recent chat messages and relevant public project notes to Google.
6. Ask “Where does the 10.96% required return come from?” Open Sources and
   supporting notes to check the answer against its evidence.

Do not enter confidential information. AI answers can still be wrong. The chat
cannot fetch live quotes, trade, provide personalised recommendations or execute
new financial calculations. Website scenario sliders remain separate.

## Retrieval, generation and source checks

The flow is: local help/boundary checks → version-filtered lexical passage search
→ relevant typed facts → one Gemini request → response/citation-ID validation →
answer and supporting evidence. A few recent same-version messages support short
follow-ups. No recursive folder ingestion, tools, browsing or arbitrary execution
is exposed to Gemini. Application instructions stay outside the retrieved corpus.

The transport uses Google's documented GenerateContent REST endpoint, an
authentication header, structured JSON output and a 25-second timeout. There
are no automatic retries, web-search tools, file uploads or new SDK dependencies.
The key is never put in a URL, prompt, widget, transcript or diagnostics. Raw
provider error bodies are discarded. Provider errors, malformed responses or
unknown source IDs fall back to project notes with a safe message.

Citation checks verify that IDs refer to supplied evidence; they do not verify
that every model claim is entailed. Lexical scores are not confidence scores.
No semantic-retrieval or final-answer accuracy metric has been measured yet.

## Usage and privacy limits

Questions are limited to 1,600 characters. At most six recent messages are sent
as context, each truncated to 1,600 characters; the UI retains at most 24 session
messages. Output is capped at 2,048 tokens. Model attempts, including failures,
count toward a 15-call session allowance, five-second cooldown and default
50-attempt daily allowance per key in the running server process.

Clear chat and analysis-version changes do not reset usage counters. The daily
allowance is in-memory: it resets on process restart, is not shared by replicas
and can be bypassed by new server processes. It is a best-effort demo guard,
NOT a guaranteed spend limit, durable rate limiter or authentication boundary.
Use provider-side quotas/usage alerts and consider restricting access before a
high-traffic launch. There is no on-disk chat logging or permanent personal memory
in this application, but external provider processing follows Google's terms.

## Check before public release

```bash
.venv/bin/python scripts/build_knowledge_base.py --check
.venv/bin/python -m unittest discover -s tests -v
```

Tests use mocked provider responses and make no paid model calls. A real owner
test after deployment must separately check key/model access, citation support,
beginner explanations, refusals, follow-ups, latency and usage. Do not describe
passing mocked tests as live Gemini verification.

Keep the unrelated local finance-model review out of an assistant-only release.
Publish the assistant/knowledge files and only the navigation/home-entry edits;
do not silently publish altered financial engines or replace the original score.

## Official references

- [Streamlit Community Cloud secrets](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management)
- [Google API key security](https://ai.google.dev/gemini-api/docs/api-key)
- [Gemini model catalogue](https://ai.google.dev/gemini-api/docs/models)
- [Gemini GenerateContent text API](https://ai.google.dev/gemini-api/docs/generate-content/text-generation)
- [Structured output](https://ai.google.dev/gemini-api/docs/generate-content/structured-output)
- [Gemini API terms](https://ai.google.dev/gemini-api/terms)
