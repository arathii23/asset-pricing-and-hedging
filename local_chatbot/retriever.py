"""MiniLM embeddings + FAISS exact cosine search, with version filtering first."""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock

import faiss
import numpy as np
import torch
from sentence_transformers import SentenceTransformer

from src.knowledge import KnowledgeBase, check_version

from .config import ARTIFACT_DIR, EMBED_MODEL, EMBED_REVISION, TOP_K, embedding_path
from .corpus import embedding_text, fingerprint, token_chunks


class Retriever:
    def __init__(
        self, kb: KnowledgeBase | None = None, artifact_dir: Path = ARTIFACT_DIR
    ):
        self.kb = kb or KnowledgeBase()
        self.directory = Path(artifact_dir)
        self.lock = Lock()
        # Tiny corpus: avoid nested native thread pools on laptop CPUs.
        torch.set_num_threads(1)
        faiss.omp_set_num_threads(1)
        path = embedding_path()
        if not (path / "model.safetensors").exists():
            raise FileNotFoundError(
                "Models are not prepared. Run: python -m local_chatbot.prepare"
            )
        self.encoder = SentenceTransformer(
            str(path),
            device="cpu",
            local_files_only=True,
            trust_remote_code=False,
            model_kwargs={"use_safetensors": True},
        )
        self.chunks = token_chunks(self.kb, self.encoder.tokenizer)
        self.corpus_hash = fingerprint(self.chunks)
        self.indexes = {}

    def build(self) -> dict:
        texts = [embedding_text(chunk) for chunk in self.chunks]
        with self.lock:
            vectors = self.encoder.encode(
                texts,
                batch_size=16,
                normalize_embeddings=True,
                show_progress_bar=True,
                convert_to_numpy=True,
            ).astype("float32")
        self.directory.mkdir(parents=True, exist_ok=True)
        np.save(self.directory / "embeddings.npy", vectors, allow_pickle=False)
        metadata = {
            "schema_version": 1,
            "embedding_model": EMBED_MODEL,
            "embedding_revision": EMBED_REVISION,
            "corpus_sha256": self.corpus_hash,
            "dimension": int(vectors.shape[1]),
            "chunk_count": len(self.chunks),
            "vectors_sha256": fingerprint(vectors.tolist()),
            "chunks": self.chunks,
        }
        (self.directory / "index.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        self._indexes(vectors)
        return {key: value for key, value in metadata.items() if key != "chunks"}

    def load(self) -> None:
        try:
            metadata = json.loads(
                (self.directory / "index.json").read_text(encoding="utf-8")
            )
            vectors = np.load(self.directory / "embeddings.npy", allow_pickle=False)
        except FileNotFoundError:
            raise FileNotFoundError(
                "Search index missing. Run: python -m local_chatbot.prepare --offline"
            ) from None
        if (
            metadata.get("corpus_sha256") != self.corpus_hash
            or metadata.get("embedding_revision") != EMBED_REVISION
            or metadata.get("chunks") != self.chunks
        ):
            raise ValueError(
                "Search index is stale. Rebuild it with python -m local_chatbot.prepare --offline"
            )
        if (
            vectors.dtype != np.float32
            or vectors.shape != (len(self.chunks), 384)
            or not np.isfinite(vectors).all()
        ):
            raise ValueError("Invalid local embedding array; rebuild the index")
        if fingerprint(vectors.tolist()) != metadata.get("vectors_sha256"):
            raise ValueError("Embedding array changed; rebuild the index")
        if not np.allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-4):
            raise ValueError("Embeddings are not normalised")
        self._indexes(vectors)

    def _indexes(self, vectors: np.ndarray) -> None:
        for version in ("resume_v1", "review_v2"):
            ids = [
                i
                for i, chunk in enumerate(self.chunks)
                if chunk["version"] in ("common", version)
            ]
            index = faiss.IndexFlatIP(vectors.shape[1])
            index.add(np.ascontiguousarray(vectors[ids], dtype=np.float32))
            self.indexes[version] = (index, ids)

    def search(
        self, query: str, version: str = "resume_v1", top_k: int = TOP_K
    ) -> list[dict]:
        check_version(version)
        if not 1 <= top_k <= 8 or not query.strip():
            raise ValueError("Provide a question and top_k between 1 and 8")
        if not self.indexes:
            self.load()
        with self.lock:
            vector = self.encoder.encode(
                [query], normalize_embeddings=True, convert_to_numpy=True
            ).astype("float32")
        index, row_ids = self.indexes[version]
        # Over-fetch, then diversify by source section to avoid repeated overlapping chunks.
        scores, neighbours = index.search(vector, min(index.ntotal, top_k * 5))
        results, sections = [], set()
        for score, local_id in zip(scores[0], neighbours[0]):
            if local_id < 0:
                continue
            chunk = self.chunks[row_ids[int(local_id)]]
            section = (chunk["document_id"], chunk["heading"])
            if section in sections:
                continue
            sections.add(section)
            results.append(
                {**chunk, "similarity": float(score), "label": f"S{len(results) + 1}"}
            )
            if len(results) == top_k:
                break
        return results
