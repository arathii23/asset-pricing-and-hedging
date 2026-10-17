"""Local Gradio UI. Run from the repository root: python -m local_chatbot.app."""

from __future__ import annotations

import argparse
import html

from .config import DEFAULT_MODEL, MAX_QUESTION_CHARS, MODELS, VERSIONS
from .pipeline import Pipeline
from .prompts import SYSTEM, chat_messages

LEARNING = """### An open-book assistant, not a finance oracle

1. **Prepare notes:** reuse the approved finance explanations, keeping original
   results separate from the later review. Do not ingest your whole computer.
2. **Split passages:** keep headings and source IDs; limit each embedding input
   to 224 MiniLM tokens, with 32 tokens of overlap between long sections.
3. **Embed:** MiniLM maps each passage to 384 numbers. Similar meanings should
   be near each other. This does not create a written answer.
4. **Retrieve:** embed your question and search normalised vectors in FAISS.
   Exact inner-product search gives cosine similarity. Scores are not confidence.
5. **Augment:** put up to three relevant source sections and your question in a
   prompt. The previous user question helps interpret short follow-ups.
6. **Generate:** Qwen writes an answer from that evidence on your computer.
   No API key, Gemini call, fine-tuning or new foundation-model training.
7. **Inspect:** check citations against the sources. A valid source ID does not
   prove the claim is true. A small model can misunderstand finance or arithmetic.

Identity/help uses a labelled FAQ, not an LLM. Unsupported questions may be
refused. Missing/invalid citations lead to a labelled source-only fallback.
The assistant is educational, not investment advice. It has no live market feed.
"""


def source_html(result: dict) -> str:
    sources = result.get("sources") or result.get("candidates", [])
    if not sources:
        return "<p>No passages retrieved for this response.</p>"
    cards = []
    for source in sources:
        title = html.escape(f"[{source['label']}] {source['heading']}")
        meta = html.escape(
            f"{source['version']} · {source['path']} · cosine similarity {source['similarity']:.3f}"
        )
        text = html.escape(source["text"])
        cards.append(
            f"<article class='source-card'><h4>{title}</h4><small>{meta}</small><pre>{text}</pre></article>"
        )
    return "".join(cards)


def build_app(pipeline: Pipeline):
    import gradio as gr

    css = """.gradio-container {max-width:1100px!important} .source-card {border:1px solid #cbd5e1;
    border-left:4px solid #0f766e;border-radius:8px;padding:14px;margin:12px 0}
    .source-card pre {white-space:pre-wrap;font-family:inherit} .source-card small {color:#475569}
    #intro {border-bottom:3px solid #0f766e;padding-bottom:12px} """
    with gr.Blocks(
        title="Finance RAG · Local learning desk",
        theme=gr.themes.Soft(primary_hue="teal", secondary_hue="blue"),
        css=css,
        analytics_enabled=False,
    ) as demo:
        gr.Markdown(
            "# Finance RAG · Local learning desk\nUnderstand the Asset Pricing and Hedging project, with inspectable sources.",
            elem_id="intro",
        )
        gr.Markdown(
            f"**On-device models:** MiniLM → FAISS → `{MODELS[pipeline.model]['id']}`. No API key. Models load on the first finance question."
        )
        with gr.Row():
            version = gr.Dropdown(
                choices=[(label, key) for key, label in VERSIONS.items()],
                value="resume_v1",
                label="Which research version?",
                scale=4,
            )
            clear = gr.Button("Clear conversation", scale=1)
        gr.Markdown(
            "Saved September 2026 evidence, not live prices. Original résumé results and later review results are not interchangeable."
        )
        state = gr.State([])
        with gr.Tab("Ask the project"):
            chat = gr.Chatbot(
                type="messages",
                height=380,
                label="Project assistant",
                sanitize_html=True,
                render_markdown=False,
                allow_tags=False,
            )
            question = gr.Textbox(
                label="Ask one small question",
                placeholder="For example: What is a share?",
                max_lines=4,
            )
            ask = gr.Button("Ask", variant="primary")
            gr.Examples(
                examples=[
                    ["Who are you?"],
                    ["What is a share?"],
                    ["Why does the company discount future cash?"],
                    ["What does WACC mean?"],
                    ["What does 0.30 Sharpe mean?"],
                    ["How does this RAG pipeline work?"],
                ],
                inputs=question,
            )
            status = gr.Markdown(
                "Ready. A first model response takes longer because weights must load into memory."
            )
            with gr.Accordion("Check the source notes for this answer", open=False):
                ask_sources = gr.HTML("No question yet.")
        with gr.Tab("Learning view · last response"):
            with gr.Accordion(
                "Public prompt instructions and formatting example", open=False
            ):
                gr.JSON(
                    value=chat_messages(
                        SYSTEM, "The question + evidence prompt below is inserted here."
                    ),
                    label="Prompt template (not model training)",
                )
            gr.Markdown(
                "### 1. Retrieval query\nA short follow-up may include the previous question."
            )
            query = gr.Textbox(label="Text embedded for search", interactive=False)
            gr.Markdown(
                "### 2. Retrieved notes\nScores are similarity, not certainty. Only passages that fit the prompt are sent to Qwen."
            )
            sources = gr.HTML("No question yet.")
            gr.Markdown("### 3. Evidence prompt given to Qwen")
            context = gr.Textbox(
                label="Question, version and evidence (no API request)",
                lines=12,
                interactive=False,
            )
            with gr.Accordion("Generation details and limitations", open=False):
                details = gr.JSON(
                    label="Last response trace (no chat is written to disk)"
                )
                raw = gr.Textbox(
                    label="Raw model text · unverified, may be incorrect",
                    lines=6,
                    interactive=False,
                )
        with gr.Tab("How RAG works"):
            gr.Markdown(LEARNING)
        gr.Markdown(
            "Educational project · Check sources and units · No uploads, trading tools or permanent memory"
        )

        def respond(text, selected, messages):
            if not text.strip():
                raise gr.Error("Please type a question.")
            if len(text.strip()) > MAX_QUESTION_CHARS:
                raise gr.Error(
                    f"Please keep the question below {MAX_QUESTION_CHARS} characters."
                )
            try:
                result = pipeline.answer(text, selected, messages)
            except (FileNotFoundError, ValueError) as exc:
                raise gr.Error(str(exc)) from None
            except Exception as exc:  # noqa: BLE001 -- UI boundary hides backend details.
                # No traceback/config/environment values are returned to the browser.
                raise gr.Error(
                    f"Local model failed ({type(exc).__name__}). Check setup, available memory, or restart with --device cpu. No generated answer was produced."
                ) from None
            updated = (
                messages
                + [
                    {"role": "user", "content": text.strip()},
                    {"role": "assistant", "content": result["answer"]},
                ]
            )[-16:]
            trace = {
                key: value
                for key, value in result.items()
                if key
                not in (
                    "sources",
                    "candidates",
                    "answer",
                    "raw_model_answer",
                    "context",
                )
            }
            label = (
                "generated draft — check the finance facts"
                if result["route"] == "generated"
                else result["route"].replace("_", " ")
            )
            return (
                "",
                updated,
                updated,
                f"**Response type: {label}.** {result['note']}",
                result["retrieval_query"],
                source_html(result),
                result["context"],
                trace,
                result.get("raw_model_answer", "No model call."),
                source_html(result),
            )

        outputs = [
            question,
            chat,
            state,
            status,
            query,
            sources,
            context,
            details,
            raw,
            ask_sources,
        ]
        ask.click(
            respond,
            [question, version, state],
            outputs,
            concurrency_limit=1,
            concurrency_id="model",
        )
        question.submit(
            respond,
            [question, version, state],
            outputs,
            concurrency_limit=1,
            concurrency_id="model",
        )

        def reset():
            return (
                "",
                [],
                [],
                "Conversation cleared. Research version kept separate.",
                "",
                "No question yet.",
                "",
                {},
                "",
                "No question yet.",
            )

        clear.click(reset, outputs=outputs, concurrency_id="model", concurrency_limit=1)
        version.change(
            reset, outputs=outputs, concurrency_id="model", concurrency_limit=1
        )
    return demo


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=MODELS, default=DEFAULT_MODEL)
    parser.add_argument(
        "--device", choices=("auto", "cpu", "mps", "cuda"), default="auto"
    )
    parser.add_argument("--port", type=int, default=7860)
    args = parser.parse_args()
    demo = build_app(Pipeline(args.model, args.device))
    demo.queue(max_size=8, default_concurrency_limit=1).launch(
        server_name="127.0.0.1",
        server_port=args.port,
        share=False,
        inbrowser=False,
        show_error=False,
        show_api=False,
        strict_cors=True,
    )


if __name__ == "__main__":
    main()
