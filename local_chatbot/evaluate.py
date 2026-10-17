"""Real retrieval and optional Qwen smoke runs. Not an automated accuracy grader."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
import time
from datetime import UTC, datetime
from pathlib import Path

from src.knowledge import KnowledgeBase, normalise

from .config import APP_DIR, DEFAULT_MODEL, EMBED_MODEL, EMBED_REVISION, MODELS, TOP_K
from .corpus import fingerprint
from .pipeline import Pipeline
from .prompts import ANSWER_CUE, EXAMPLE_ANSWER, EXAMPLE_USER, SYSTEM

GENERATE_IDS = (
    "share",
    "borrow",
    "discount",
    "rates",
    "wacc",
    "collar",
    "walk",
    "sharpe",
    "units",
    "npv_calc",
    "review_scores",
    "rag",
    "unknown_personal",
    "unknown_live",
    "injection",
    "guarantee",
)


def diverse(rows, top_k=TOP_K):
    result, seen = [], set()
    for row in rows:
        section = row["document_id"], row["heading"]
        if section not in seen:
            seen.add(section)
            result.append(row)
        if len(result) == top_k:
            break
    return result


def run(model=DEFAULT_MODEL, device="auto", retrieval_only=False):
    from .retriever import Retriever

    kb = KnowledgeBase()
    cases = json.loads((kb.root / "eval/questions.json").read_text(encoding="utf-8"))[
        "cases"
    ]
    retriever = Retriever(kb)
    retriever.load()
    # Same token passages, version filter and section diversity for the lexical baseline.
    baseline = KnowledgeBase()
    baseline.chunks = [{**chunk, "tags": []} for chunk in retriever.chunks]
    retrieval = []
    for case in cases:
        if case.get("intent") or not case.get("grade_retrieval", True):
            continue
        version = case.get("version", "resume_v1")
        expected = [
            "local_rag" if doc in ("assistant", "rag") else doc
            for doc in case["expected_docs"]
        ]

        def supports(row, expected=expected, case=case):
            return row["document_id"] in expected and (
                row["document_id"] == "local_rag"
                or not case.get("expected_heading_terms")
                or any(
                    normalise(term) in normalise(row["heading"])
                    for term in case["expected_heading_terms"]
                )
            )

        semantic = retriever.search(case["question"], version)
        lexical = diverse(baseline.search(case["question"], version, top_k=15))
        if any(row["version"] not in ("common", version) for row in semantic):
            raise ValueError("Version leakage in retrieved evidence")
        retrieval.append(
            {
                "id": case["id"],
                "version": version,
                "semantic_hit": any(map(supports, semantic)),
                "lexical_hit": any(map(supports, lexical)),
                "top_similarity": semantic[0]["similarity"],
                "semantic_sources": [row["id"] for row in semantic],
                "lexical_sources": [row["id"] for row in lexical],
            }
        )
    report = {
        "schema_version": 1,
        "ran_at_utc": datetime.now(UTC).isoformat(),
        "meaning": "Reference evidence hit@3 and actual response smoke runs, NOT generated-answer accuracy or an untouched benchmark.",
        "platform": {
            "os": platform.system(),
            "architecture": platform.machine(),
            "python": platform.python_version(),
        },
        "packages": {
            name: importlib.metadata.version(name)
            for name in (
                "torch",
                "transformers",
                "sentence-transformers",
                "faiss-cpu",
                "gradio",
                "numpy",
            )
        },
        "embedding_model": EMBED_MODEL,
        "embedding_revision": EMBED_REVISION,
        "prompt_template_sha256": fingerprint(
            [SYSTEM, ANSWER_CUE, EXAMPLE_USER, EXAMPLE_ANSWER]
        ),
        "system_prompt": SYSTEM,
        "answer_cue": ANSWER_CUE,
        "citation_format_example": {"user": EXAMPLE_USER, "assistant": EXAMPLE_ANSWER},
        "corpus_sha256": retriever.corpus_hash,
        "chunk_count": len(retriever.chunks),
        "top_k": TOP_K,
        "retrieval_summary": {
            "cases": len(retrieval),
            "semantic_hits": sum(row["semantic_hit"] for row in retrieval),
            "lexical_hits": sum(row["lexical_hit"] for row in retrieval),
            "wrong_version_passages": 0,
        },
        "retrieval": retrieval,
        "responses": [],
    }
    print(json.dumps(report["retrieval_summary"]), flush=True)
    if not retrieval_only:
        pipeline = Pipeline(model, device, retriever=retriever)
        for case in cases:
            if case["id"] not in GENERATE_IDS:
                continue
            started = time.perf_counter()
            result = pipeline.answer(case["question"], case.get("version", "resume_v1"))
            row = {
                "id": case["id"],
                "question": case["question"],
                "version": result["version"],
                "route": result["route"],
                "answer": result["answer"],
                "raw_model_answer": result.get("raw_model_answer"),
                "note": result["note"],
                "elapsed_seconds": round(time.perf_counter() - started, 3),
                "generation_seconds": result.get("generation_seconds"),
                "prompt_tokens": result.get("prompt_tokens"),
                "generated_tokens": result.get("generated_tokens"),
                "sources": [
                    {
                        k: s[k]
                        for k in (
                            "id",
                            "label",
                            "text",
                            "heading",
                            "version",
                            "similarity",
                        )
                    }
                    for s in result["sources"]
                ],
            }
            report["responses"].append(row)
            print(
                f"{case['id']}: {result['route']} · {row['elapsed_seconds']}s · {result['answer']}",
                flush=True,
            )
        report["generator"] = {
            **MODELS[model],
            "device": pipeline.generator.device,
            "dtype": str(pipeline.generator.model.dtype),
        }
        import psutil

        report["process_rss_mib_after_run"] = round(
            psutil.Process().memory_info().rss / 1024**2
        )
        if pipeline.generator.device == "mps":
            import torch

            report["mps_allocated_mib_after_run"] = round(
                torch.mps.current_allocated_memory() / 1024**2
            )
            report["mps_driver_allocated_mib_after_run"] = round(
                torch.mps.driver_allocated_memory() / 1024**2
            )
        report["memory_note"] = (
            "End-of-run process/accelerator snapshots, not peak RAM; shared/unified allocations can overlap."
        )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=MODELS, default=DEFAULT_MODEL)
    parser.add_argument(
        "--device", choices=("auto", "cpu", "mps", "cuda"), default="auto"
    )
    parser.add_argument("--retrieval-only", action="store_true")
    parser.add_argument(
        "--output", type=Path, default=APP_DIR / "evaluation/latest.json"
    )
    args = parser.parse_args()
    report = run(args.model, args.device, args.retrieval_only)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Report saved to {args.output}")


if __name__ == "__main__":
    main()
