"""Allowlisted finance notes -> token-bounded passages with traceable metadata.

This uses the existing knowledge-base loader, NOT recursive folder ingestion.
The embedding tokenizer's offsets preserve original Markdown and number formatting.
"""

from __future__ import annotations

import hashlib
import json
import re

from src.knowledge import KnowledgeBase

from .config import APP_DIR, MAX_EMBED_TOKENS, OVERLAP_TOKENS


def fingerprint(value) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()


def embedding_text(chunk: dict) -> str:
    return f"{chunk['title']}\n{chunk['heading']}\n{chunk['text']}"


def token_chunks(kb: KnowledgeBase, tokenizer) -> list[dict]:
    chunks = []
    # The website's assistant/provider notes describe a different Gemini runtime.
    # Finance notes are reused unchanged; local runtime notes replace those two docs.
    parents = [c for c in kb.chunks if c["document_id"] not in ("assistant", "rag")]
    sections = re.split(
        r"^## (.+)$",
        (APP_DIR / "knowledge.md").read_text(encoding="utf-8"),
        flags=re.MULTILINE,
    )
    for heading, body in zip(sections[1::2], sections[2::2]):
        parents.append(
            {
                "id": "common:local_rag:" + fingerprint(heading)[:12],
                "document_id": "local_rag",
                "title": "Local finance RAG assistant",
                "heading": heading,
                "version": "common",
                "path": "local_chatbot/knowledge.md",
                "sources": ["local_chatbot implementation"],
                "text": body.strip(),
            }
        )
    for parent in parents:
        prefix = f"{parent['title']}\n{parent['heading']}\n"
        budget = (
            MAX_EMBED_TOKENS
            - len(tokenizer.encode(prefix, add_special_tokens=True))
            - 4
        )
        if budget <= OVERLAP_TOKENS:
            raise ValueError("Heading too long for embedding token budget")
        offsets = tokenizer(
            parent["text"],
            add_special_tokens=False,
            return_offsets_mapping=True,
            truncation=False,
            verbose=False,
        )["offset_mapping"]
        start, part = 0, 0
        while start < len(offsets):
            stop = min(start + budget, len(offsets))
            text = parent["text"][offsets[start][0] : offsets[stop - 1][1]].strip()
            row = {
                key: parent[key]
                for key in (
                    "document_id",
                    "title",
                    "heading",
                    "version",
                    "path",
                    "sources",
                )
            }
            row.update(
                parent_id=parent["id"],
                text=text,
                part=part,
                id=parent["id"] + f":token-{part}:{fingerprint(text)[:8]}",
            )
            row["embedding_tokens"] = len(
                tokenizer.encode(embedding_text(row), add_special_tokens=True)
            )
            if row["embedding_tokens"] > MAX_EMBED_TOKENS:
                raise ValueError(
                    "A passage would be silently truncated; fix chunking first"
                )
            chunks.append(row)
            if stop == len(offsets):
                break
            start, part = stop - OVERLAP_TOKENS, part + 1
    if not chunks:
        raise ValueError("No approved source passages found")
    return chunks
