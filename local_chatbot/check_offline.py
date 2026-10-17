"""One real answer with Python socket connections blocked. Prepare models first."""

import argparse
import json
import socket
from unittest.mock import patch

from .config import DEFAULT_MODEL, MODELS
from .pipeline import Pipeline


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=MODELS, default=DEFAULT_MODEL)
    parser.add_argument(
        "--device", choices=("auto", "cpu", "mps", "cuda"), default="auto"
    )
    args = parser.parse_args()
    with patch.object(
        socket.socket,
        "connect",
        side_effect=AssertionError("Network connection attempted"),
    ) as connections:
        result = Pipeline(args.model, args.device).answer("What is a share?")
    print(
        json.dumps(
            {
                "question": result["question"],
                "answer": result["answer"],
                "route": result["route"],
                "model": result.get("model"),
                "device": result.get("device"),
                "dtype": result.get("dtype"),
                "socket_connect_attempts": connections.call_count,
            },
            indent=2,
        )
    )
    if connections.call_count or result["route"] != "generated":
        raise SystemExit(
            "Offline check did not produce a generated answer without socket connections"
        )


if __name__ == "__main__":
    main()
