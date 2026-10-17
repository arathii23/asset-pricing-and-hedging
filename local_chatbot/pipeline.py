"""Visible orchestration: scope -> retrieve -> pack evidence -> generate -> check IDs."""

from __future__ import annotations

import json
import re
import time

from src.knowledge import FAQ_LOOKUP, check_version, normalise

from .config import (
    DEFAULT_MODEL,
    MAX_CONTEXT_TOKENS,
    MAX_QUESTION_CHARS,
    MIN_SIMILARITY,
    MODELS,
    VERSIONS,
)
from .prompts import ANSWER_CUE, SYSTEM, chat_messages


def direct_reply(question: str, model: str = DEFAULT_MODEL) -> str | None:
    """Exact FAQ aliases only, so a compound finance question still uses retrieval."""
    intent = FAQ_LOOKUP.get(normalise(question))
    replies = {
        "identity": "I'm the Asset Pricing and Hedging Assistant. I help you understand this finance project using its saved notes. Try: ‘What is a share?’",
        "greeting": "Hello! I can help explain this finance project one small step at a time. Try: ‘What problem does this project solve?’",
        "capabilities": "I can explain finance basics, saved project results and the portfolio ML experiment, with sources. The learning view shows retrieval and the evidence given to Qwen. I cannot fetch live prices, trade or give personalised investment advice.",
        "provider": f"This local app uses {MODELS[model]['id']} for generated answers, MiniLM for embeddings and FAISS for retrieval. It does not call Gemini or ChatGPT. This particular reply is a local FAQ, not an LLM response.",
        "status": "This is the local MiniLM → FAISS → Qwen app. Finance questions run retrieval and generation when the downloaded models are ready. This status reply is a local FAQ; it does not test the model connection. No hosted API key is used.",
        "live": "I cannot fetch live prices or execute trades. The project uses a saved September 2026 snapshot, not a live market feed.",
        "memory": "There is no permanent memory. Chat is held in this browser session's server memory; the previous question can help interpret a follow-up. Clearing chat or changing version removes that context.",
        "navigation": "Start with ‘What is a share?’, then ‘What is a cash flow?’ and ‘Why discount future cash?’. Choose the original résumé experiment or the later review before asking about results. Open the learning view to inspect the sources.",
    }
    if intent in replies:
        return replies[intent]
    q = normalise(question)
    if re.search(
        r"\b(api key|secret|password|hidden files|system prompt)\b", q
    ) and re.search(r"\b(show|print|reveal|read|give|ignore)\b", q):
        return "I cannot access or disclose credentials or hidden files. This app only searches explicitly approved project notes; it has no file-reading tool available to the language model."
    if re.search(r"\b(right now|today|current|live)\b", q) and re.search(
        r"\b(price|prices|trading|sharpe|quote)\b", q
    ):
        return "I cannot verify current prices or the live website's state. I only have the saved project snapshot and the selected research version."
    if (
        "guarantee" in q
        or "guaranteed" in q
        or re.search(r"\b(which stock|what stock)\b.*\bbuy\b", q)
    ):
        return "I cannot recommend a stock for you or guarantee returns. I can explain the project's historical risk and return measures; they do not establish future profits."
    if "personally" in q and re.search(r"\b(code|coded|build|built|contribution)\b", q):
        return "The saved code and notes cannot verify who personally wrote each part or when. That needs your own contribution records; I should not invent an interview claim."
    return None


def retrieval_query(question: str, history: list[dict]) -> tuple[str, str]:
    followup = bool(
        re.search(
            r"\b(that|this|it|those|these|simpler|continue|again)\b", question.lower()
        )
    )
    previous = next(
        (row["content"] for row in reversed(history) if row["role"] == "user"), ""
    )
    previous = (
        previous[:MAX_QUESTION_CHARS] if followup and len(question.split()) < 18 else ""
    )
    return (f"{previous}\nFollow-up: {question}" if previous else question), previous


def citation_check(answer: str, sources: list[dict]) -> tuple[bool, str]:
    used = set(re.findall(r"\[S(\d+)\]", answer))
    allowed = {source["label"][1:] for source in sources}
    if not used:
        return False, "Qwen did not provide source citations."
    if not used.issubset(allowed):
        return False, "Qwen cited an unknown source ID."
    return True, "Citation IDs are valid; this does not prove factual support."


def parse_answer(raw: str, sources: list[dict]) -> str:
    """A structured model reply is data, not trusted markup or a tool call."""
    text = raw.strip()
    if text.startswith("```json") and text.endswith("```"):
        text = text[7:-3].strip()
    record = json.loads(text)
    if not isinstance(record, dict) or set(record) != {"answer", "source_ids"}:
        raise ValueError("Qwen did not return the required answer/source structure.")
    answer, ids = record["answer"], record["source_ids"]
    if not isinstance(answer, str) or not answer.strip() or len(answer) > 2400:
        raise ValueError("Qwen returned an invalid answer field.")
    if (
        not isinstance(ids, list)
        or not ids
        or len(ids) > 3
        or not all(isinstance(label, str) for label in ids)
    ):
        raise ValueError("Qwen did not supply valid source IDs.")
    if not set(ids).issubset({source["label"] for source in sources}):
        raise ValueError("Qwen cited an unknown source ID.")
    return (
        answer.strip()
        + "\n\nSources: "
        + " ".join(f"[{label}]" for label in dict.fromkeys(ids))
    )


class Pipeline:
    def __init__(
        self, model=DEFAULT_MODEL, device="auto", retriever=None, generator=None
    ):
        if model not in MODELS:
            raise ValueError("Choose small or larger")
        self.model, self.device = model, device
        self._retriever, self._generator = retriever, generator

    @property
    def retriever(self):
        if self._retriever is None:
            from .retriever import Retriever

            self._retriever = Retriever()
            self._retriever.load()
        return self._retriever

    @property
    def generator(self):
        if self._generator is None:
            from .generator import Generator

            self._generator = Generator(self.model, self.device)
        return self._generator

    def answer(self, question: str, version="resume_v1", history=None) -> dict:
        check_version(version)
        question = question.strip()
        if not question or len(question) > MAX_QUESTION_CHARS:
            raise ValueError(
                f"Ask a question between 1 and {MAX_QUESTION_CHARS} characters"
            )
        started = time.perf_counter()
        direct = direct_reply(question, self.model)
        result = {
            "question": question,
            "version": version,
            "sources": [],
            "context": "",
            "retrieval_query": question,
        }
        if direct:
            return {
                **result,
                "answer": direct,
                "route": "local_faq_or_boundary",
                "note": "No LLM call was made.",
            }
        query, previous = retrieval_query(question, history or [])
        candidates = self.retriever.search(query, version)
        result.update(
            retrieval_query=query,
            candidates=candidates,
            retrieval_seconds=round(time.perf_counter() - started, 3),
        )
        if not candidates or candidates[0]["similarity"] < MIN_SIMILARITY:
            return {
                **result,
                "answer": "I could not find sufficiently relevant project notes. Try naming a project topic, such as WACC, the expansion or currency hedging.",
                "route": "no_evidence",
                "note": "No LLM call. Similarity threshold is heuristic, not confidence.",
            }
        generator = self.generator
        header = f"Research version: {VERSIONS[version]} ({version}).\n"
        if previous:
            header += f"Previous user question (topic only, not evidence): {previous}\n"
        header += f"Question: {question}\n\nEVIDENCE:\n"
        context, sources = "", []
        for candidate in candidates:
            if candidate["similarity"] < MIN_SIMILARITY:
                continue
            block = f"[{candidate['label']}] {candidate['title']} — {candidate['heading']} ({candidate['version']})\n{candidate['text']}\n\n"
            messages = chat_messages(
                SYSTEM,
                header + context + block + f"Question: {question}\n" + ANSWER_CUE,
            )
            tokens = generator.tokenizer.apply_chat_template(
                messages, tokenize=True, add_generation_prompt=True
            )
            if len(tokens) <= MAX_CONTEXT_TOKENS:
                context += block
                sources.append(candidate)
        if not sources:
            raise ValueError(
                "Evidence did not fit the prompt budget. Ask a shorter question."
            )
        prompt = header + context + f"Question: {question}\n" + ANSWER_CUE
        generated = generator.generate(SYSTEM, prompt)
        try:
            answer = parse_answer(generated["text"], sources)
            valid, note = citation_check(answer, sources)
        except (ValueError, TypeError):
            answer, valid, note = (
                "",
                False,
                "Qwen did not return a valid, source-labelled JSON answer.",
            )
        # Disable model-created external links/media. Source paths are displayed separately.
        answer = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", answer)
        answer = re.sub(r"https?://\S+", "[external link omitted]", answer)
        if generated["hit_output_limit"] or generated.get("hit_time_limit", False):
            valid, note = (
                False,
                "Qwen reached its output/time limit; a potentially incomplete answer was not presented as complete.",
            )
        if not valid:
            answer = "I could not produce a properly cited, complete answer. Please read the retrieved notes in the learning view. This is a source-only fallback, not a successful generated answer."
        return {
            **result,
            **{k: v for k, v in generated.items() if k != "text"},
            "answer": answer,
            "route": "generated" if valid else "source_only_fallback",
            "note": note,
            "sources": sources,
            "context": prompt,
            "raw_model_answer": generated["text"],
            "total_seconds": round(time.perf_counter() - started, 3),
        }
