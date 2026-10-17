"""Small, explicit defaults: model IDs, immutable revisions and local directories."""

from __future__ import annotations

import os
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
ROOT = APP_DIR.parent
KNOWLEDGE_DIR = ROOT / "knowledge_base"
CACHE_DIR = APP_DIR / ".cache"
ARTIFACT_DIR = APP_DIR / "artifacts"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBED_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
MODELS = {
    "small": {
        "id": "Qwen/Qwen2.5-0.5B-Instruct",
        "revision": "7ae557604adf67be50417f59c2c2f167def9a775",
    },
    "larger": {
        "id": "Qwen/Qwen2.5-1.5B-Instruct",
        "revision": "989aa7980e4cf806f80c7fef2b1adb7bc71aa306",
    },
}
DEFAULT_MODEL = "larger"
VERSIONS = {
    "resume_v1": "Original résumé experiment",
    "review_v2": "Later reviewed extension",
}
MAX_EMBED_TOKENS = 224  # Below MiniLM's 256-wordpiece limit, including headings.
OVERLAP_TOKENS = 32
TOP_K = 3
MIN_SIMILARITY = 0.30  # Heuristic demo gate, NOT a probability or confidence score.
MAX_QUESTION_CHARS = 1200
MAX_CONTEXT_TOKENS = 1800
MAX_NEW_TOKENS = 220


def model_path(kind: str) -> Path:
    if kind not in MODELS:
        raise ValueError("Choose small or larger")
    return CACHE_DIR / "models" / f"qwen-{kind}-{MODELS[kind]['revision'][:12]}"


def embedding_path() -> Path:
    return CACHE_DIR / "models" / f"minilm-{EMBED_REVISION[:12]}"


def private_runtime() -> None:
    # Process-local settings, never credentials. Model fetching explicitly uses token=False.
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"
    os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"


private_runtime()
