"""Explicit one-time public-model download and local embedding-index build."""

from __future__ import annotations

import argparse
import json

from .config import (
    CACHE_DIR,
    DEFAULT_MODEL,
    EMBED_MODEL,
    EMBED_REVISION,
    MODELS,
    embedding_path,
    model_path,
)


def download_models(model: str) -> None:
    from huggingface_hub import snapshot_download

    files = [
        "*.json",
        "*.safetensors",
        "*.txt",
        "*.model",
        "merges.txt",
        "README.md",
        "LICENSE",
        "1_Pooling/config.json",
    ]
    for name, revision, destination in (
        (EMBED_MODEL, EMBED_REVISION, embedding_path()),
        (MODELS[model]["id"], MODELS[model]["revision"], model_path(model)),
    ):
        print(f"Downloading public model: {name} @ {revision[:12]}", flush=True)
        snapshot_download(
            name,
            revision=revision,
            local_dir=destination,
            cache_dir=CACHE_DIR / "hub",
            allow_patterns=files,
            ignore_patterns=["onnx/*", "openvino/*", "*.bin", "*.py", "*.h5", "*.ot"],
            token=False,
            max_workers=3,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=MODELS, default=DEFAULT_MODEL)
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Rebuild using already downloaded model files only",
    )
    args = parser.parse_args()
    if not args.offline:
        download_models(args.model)
    if not (model_path(args.model) / "model.safetensors").exists():
        raise FileNotFoundError(
            "Selected Qwen model is missing. Run preparation without --offline first."
        )
    from .retriever import Retriever

    metadata = Retriever().build()
    print(json.dumps(metadata, indent=2))
    print(f"Ready. Start the app: python -m local_chatbot.app --model {args.model}")


if __name__ == "__main__":
    main()
