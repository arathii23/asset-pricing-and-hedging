"""Command-line interface, also useful for verifying real model responses."""

import argparse
import json

from .config import DEFAULT_MODEL, MODELS, VERSIONS
from .pipeline import Pipeline


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question")
    parser.add_argument("--version", choices=VERSIONS, default="resume_v1")
    parser.add_argument("--model", choices=MODELS, default=DEFAULT_MODEL)
    parser.add_argument(
        "--device", choices=("auto", "cpu", "mps", "cuda"), default="auto"
    )
    parser.add_argument("--trace", action="store_true")
    args = parser.parse_args()
    result = Pipeline(args.model, args.device).answer(args.question, args.version)
    print(
        json.dumps(result, ensure_ascii=False, indent=2)
        if args.trace
        else result["answer"]
    )


if __name__ == "__main__":
    main()
