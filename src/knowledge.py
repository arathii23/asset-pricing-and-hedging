"""Offline, allowlisted knowledge preparation and FAQ support. No model/network calls.

Lexical search is a development baseline, not semantic RAG or answer generation.
The eventual app must supply trusted instructions, version and runtime capabilities.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path, PurePosixPath

DEFAULT_ROOT = Path(__file__).resolve().parents[1] / "knowledge_base"
VERSIONS = ("resume_v1", "review_v2")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_path(root: Path, relative: str) -> Path:
    """Confine explicitly approved paths, including symlink resolution."""
    parts = PurePosixPath(relative)
    if parts.is_absolute() or ".." in parts.parts or "\\" in relative or not parts.parts:
        raise ValueError(f"Unsafe knowledge path: {relative}")
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"Knowledge path escapes root: {relative}")
    return path


def normalise(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(c for c in value if not unicodedata.combining(c))
    return " ".join(re.findall(r"[a-z0-9]+(?:\.[0-9]+)?", value))


STOP = set("a an the is are am was were be to of for and or in on at it this that i you your me my we our do does did can could how what who why will with from as by about if so have has much please tell explain".split())


def tokens(value: str) -> list[str]:
    return [word for word in normalise(value).split() if word not in STOP]


def check_version(version: str) -> None:
    if version not in VERSIONS:
        raise ValueError(f"Select a known version: {', '.join(VERSIONS)}")


def make_chunks(root: Path = DEFAULT_ROOT) -> list[dict]:
    """Index only explicit document entries. Config/source files cannot enter here."""
    manifest = read_json(root / "manifest.json")
    chunks, seen_docs = [], set()
    for document in manifest["documents"]:
        if document["id"] in seen_docs:
            raise ValueError("Duplicate document ID")
        seen_docs.add(document["id"])
        if document["version"] not in ("common", *VERSIONS):
            raise ValueError("Unknown document version")
        if not set(document["sources"]).issubset(manifest["sources"]):
            raise ValueError("Unregistered document source")
        relative = document["path"]
        if not relative.startswith("documents/") or not relative.endswith(".md"):
            raise ValueError("Only allowlisted documents/*.md can be indexed")
        source = safe_path(root, relative).read_text(encoding="utf-8")
        sections = re.split(r"^## (.+)$", source, flags=re.MULTILINE)
        if len(sections) < 3:
            raise ValueError(f"Document has no named sections: {relative}")
        for heading, body in zip(sections[1::2], sections[2::2]):
            # Preserve complete paragraphs, especially formulas/tables.
            groups, group = [], []
            for paragraph in body.strip().split("\n\n"):
                if len(paragraph.split()) > 300:
                    raise ValueError(f"Split overlong paragraph in {relative}: {heading}")
                if group and sum(len(p.split()) for p in group) + len(paragraph.split()) > 300:
                    groups.append("\n\n".join(group))
                    group = []
                group.append(paragraph)
            if group:
                groups.append("\n\n".join(group))
            for part, text in enumerate(groups, 1):
                content_hash = digest(text.encode())
                slug = normalise(heading).replace(" ", "-")
                chunk_id = f"{document['version']}:{document['id']}:{slug}:{part}:{content_hash[:10]}"
                chunks.append({
                    "id": chunk_id, "document_id": document["id"],
                    "version": document["version"], "title": document["title"],
                    "heading": heading.strip(), "part": part, "text": text,
                    "path": relative, "sources": document["sources"],
                    "tags": document.get("tags", []), "content_sha256": content_hash,
                    "citation": f"{document['title']} — {heading.strip()} [{document['version']}]",
                })
    if len({c["id"] for c in chunks}) != len(chunks):
        raise ValueError("Duplicate passage IDs")
    return chunks


FAQ_ALIASES = {
    "greeting": ("hi", "hello", "hey", "good morning", "good evening"),
    "identity": ("who are you", "what is your name", "introduce yourself", "what are you", "who is this assistant", "who is the chatbot"),
    "capabilities": ("what can you do", "what do you do", "what can this chatbot do", "what can you help me with", "help", "how can you help me", "how can i use you", "what are your capabilities", "who are you and what can you help me with"),
    "provider": ("are you gemini or chatgpt", "which model are you", "are you gemini", "are you chatgpt", "who powers you"),
    "navigation": ("how do i use the website", "how do i use this website", "where should i start", "how do i use this app"),
    "live": ("can you fetch live prices", "can you trade", "can you execute trades", "can you get current prices"),
    "memory": ("do you remember me", "do you have memory", "will you remember this conversation"),
    "status": ("is the chatbot connected", "are you connected to gemini", "is rag live", "what is implemented now"),
}
FAQ_LOOKUP = {normalise(alias): intent for intent, aliases in FAQ_ALIASES.items() for alias in aliases}


class KnowledgeBase:
    def __init__(self, root: Path = DEFAULT_ROOT, profile: dict | None = None):
        self.root = Path(root)
        self.manifest = read_json(self.root / "manifest.json")
        # Only the trusted application can supply profile overrides. Never use user text.
        self.profile = read_json(self.root / "assistant_profile.json") if profile is None else profile
        self.chunks = make_chunks(self.root)

    def facts(self, version: str = "resume_v1") -> dict:
        check_version(version)
        facts = read_json(self.root / "facts" / f"{version}.json")
        if facts["version"] != version:
            raise ValueError("Fact/version mismatch")
        return facts

    def fact(self, name: str, version: str = "resume_v1") -> dict:
        """Return a typed record including units/provenance, never a bare ambiguous number."""
        return self.facts(version)["facts"][name]

    def basic_reply(self, question: str) -> dict | None:
        """Exact high-confidence FAQ only; compound finance questions go to retrieval.

        This is not a safety classifier or a substitute for the later LLM guardrails.
        Unknown questions return None, not a guessed answer.
        """
        intent = FAQ_LOOKUP.get(normalise(question))
        if not intent:
            return None
        caps = self.profile["capabilities"]
        if not caps["basic_faq"] or (intent == "memory" and caps["persistent_personal_memory"]):
            return None
        name = self.profile["name"]
        replies = {
            "identity": f"I'm the {name}, a beginner-friendly guide to this finance project. I explain its methods, saved results and limitations. I'm not the project author or a financial adviser.",
            "capabilities": "I can explain shares, cash flows, CAPM, WACC, valuation, currency hedges and the portfolio ML experiment, and point you to project sources. Start with: ‘What problem does this project solve?’",
            "greeting": f"Hi! I'm the {name}. I can help you understand the project step by step. Would you like a simple overview or help with a particular term?",
            "navigation": "Start with Overview for the three project questions. Then visit Expansion analysis, Currency hedging, Portfolio analysis or Option pricing. Methods & data explains assumptions and terminology. Try one input at a time and compare it with the saved base case.",
            "memory": "I don't have permanent personal memory in this project. A future chat screen may use the visible conversation during your session; don't share confidential information or API keys.",
        }
        if intent == "provider":
            if caps["generative_answers"] and self.profile.get("connected_model"):
                answer = f"The configured answer model is {self.profile['connected_model']}. I use project notes as reference material; I was not trained from scratch on this project."
            else:
                answer = "Gemini is not connected in this offline helper. The website may enable it using private server settings. This reply is a local FAQ template, not a Gemini or ChatGPT model response. No model was trained on the project."
        elif intent == "live":
            if caps["live_market_data"] or caps["trade_execution"]:
                return None  # A future tool integration must describe its real scope.
            answer = "I do not fetch live prices or execute trades. I explain the project's saved snapshot, assumptions and historical experiments; they are not today's market quotes."
        elif intent == "status":
            if caps["generative_answers"] or caps["semantic_retrieval"]:
                return None  # Do not hard-code a stale deployment claim.
            answer = "The knowledge base, offline keyword retrieval and basic FAQ replies are prepared. Gemini generation and semantic retrieval are not connected yet in this offline helper; the website reports its actual runtime status separately."
        else:
            answer = replies[intent]
        source_doc = "project" if intent == "navigation" else "assistant"
        return {"intent": intent, "answer": answer, "route": "local_faq", "document_id": source_doc,
                "sources": [{"path": d["path"], "title": d["title"], "version": "common"}
                            for d in self.manifest["documents"] if d["id"] == source_doc]}

    def search(self, question: str, version: str = "resume_v1", top_k: int = 4,
               include_comparison: bool = False) -> list[dict]:
        """Transparent, version-filtered BM25-like lexical baseline. No network."""
        check_version(version)
        if not 1 <= top_k <= 20:
            raise ValueError("top_k must be between 1 and 20")
        allowed = {"common", *VERSIONS} if include_comparison else {"common", version}
        corpus = [c for c in self.chunks if c["version"] in allowed]
        query = set(tokens(question))
        if not query:
            return []
        counts = [Counter(tokens(c["text"])) for c in corpus]
        average_length = sum(sum(count.values()) for count in counts) / max(len(counts), 1)
        frequencies = {term: sum(term in count for count in counts) for term in query}
        results = []
        for chunk, count in zip(corpus, counts):
            length = sum(count.values())
            heading_tokens = set(tokens(chunk["heading"]))
            title_tokens = set(tokens(chunk["title"]))
            tag_tokens = set(tokens(" ".join(chunk["tags"])))
            score = 0.0
            for term in query:
                df = frequencies[term]
                idf = math.log(1 + (len(corpus) - df + .5) / (df + .5))
                tf = count[term]
                bm = tf * 2.2 / (tf + 1.2 * (.25 + .75 * length / average_length)) if tf else 0
                score += idf * (bm + 3 * (term in heading_tokens) + .4 * (term in title_tokens) + .1 * (term in tag_tokens))
            if score > 0:
                results.append({**chunk, "score": round(score, 6)})
        return sorted(results, key=lambda row: (-row["score"], row["id"]))[:top_k]


def evaluate_retrieval(kb: KnowledgeBase, top_k: int = 4) -> dict:
    """Check reference evidence hits and exact FAQ templates; no LLM grading."""
    cases = read_json(kb.root / "eval/questions.json")["cases"]
    details, hit_count, graded, faq_count = [], 0, 0, 0
    for case in cases:
        reply = kb.basic_reply(case["question"])
        actual_intent = reply["intent"] if reply else None
        if "intent" in case and actual_intent != case["intent"]:
            raise ValueError(f"FAQ intent mismatch: {case['id']}")
        if case.get("intent"):
            faq_count += 1
            for phrase in case.get("answer_contains", []):
                if normalise(phrase) not in normalise(reply["answer"]):
                    raise ValueError(f"FAQ missing expected content: {case['id']}: {phrase}")
            if reply["document_id"] not in case["expected_docs"]:
                raise ValueError(f"FAQ points to the wrong evidence: {case['id']}")
            details.append({"id": case["id"], "type": "exact_faq_template", "passed": True,
                            "evidence_document": reply["document_id"]})
            continue
        if not case.get("grade_retrieval", True):
            details.append({"id": case["id"], "type": "future_answer_review", "automated_answer_grade": None})
            continue
        hits = kb.search(case["question"], version=case.get("version", "resume_v1"), top_k=top_k)
        def supports(chunk):
            return chunk["document_id"] in case["expected_docs"] and (
                not case.get("expected_heading_terms") or any(
                    normalise(term) in normalise(chunk["heading"]) for term in case["expected_heading_terms"]))
        passed = any(supports(chunk) for chunk in hits)
        graded += 1
        hit_count += passed
        details.append({"id": case["id"], "type": "lexical_evidence_hit", "passed": passed,
                        "passage_ids": [chunk["id"] for chunk in hits]})
    return {"test_type": "lexical retrieval smoke test, NOT semantic or generated-answer accuracy",
            "top_k": top_k, "reference_cases": len(cases), "graded_retrieval_cases": graded,
            "evidence_hits": hit_count, "evidence_hit_rate": hit_count / graded if graded else None,
            "exact_faq_cases_passed": faq_count, "llm_answers_evaluated": 0, "details": details}
