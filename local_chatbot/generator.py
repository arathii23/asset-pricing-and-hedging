"""Qwen text generation, entirely on this computer after explicit model setup."""

from __future__ import annotations

import time
from threading import Lock

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    LogitsProcessor,
    LogitsProcessorList,
    StoppingCriteria,
    StoppingCriteriaList,
)

from .config import (
    DEFAULT_MODEL,
    MAX_CONTEXT_TOKENS,
    MAX_NEW_TOKENS,
    MODELS,
    model_path,
)
from .prompts import chat_messages


class Deadline(StoppingCriteria):
    def __init__(self, seconds: float):
        self.end = time.monotonic() + seconds

    def __call__(self, input_ids, scores, **kwargs):
        return time.monotonic() >= self.end


class FiniteLogits(LogitsProcessor):
    """Stop numeric failure explicitly instead of displaying repeated junk tokens."""

    def __call__(self, input_ids, scores):
        if torch.isnan(scores).any() or torch.isposinf(scores).any():
            raise FloatingPointError("Non-finite model logits; try the CPU runtime")
        return scores


class Generator:
    def __init__(self, model: str = DEFAULT_MODEL, device: str = "auto"):
        if model not in MODELS:
            raise ValueError("Choose small or larger")
        if device == "auto":
            device = (
                "cuda"
                if torch.cuda.is_available()
                else "mps"
                if torch.backends.mps.is_available()
                else "cpu"
            )
        if device not in ("cpu", "mps", "cuda"):
            raise ValueError("Device must be auto, cpu, mps or cuda")
        path = model_path(model)
        if not (path / "model.safetensors").exists():
            raise FileNotFoundError(
                f"Prepare the {model} model first: python -m local_chatbot.prepare --model {model}"
            )
        self.name, self.revision, self.device = (
            MODELS[model]["id"],
            MODELS[model]["revision"],
            device,
        )
        self.tokenizer = AutoTokenizer.from_pretrained(
            str(path), local_files_only=True, trust_remote_code=False
        )
        # Qwen's native BF16 range matters: FP16 overflowed on our MPS test.
        # Never silently use a numerically broken accelerator format.
        if device == "mps":
            try:
                torch.zeros(1, dtype=torch.bfloat16, device="mps")
            except (RuntimeError, TypeError):
                raise ValueError(
                    "This Mac runtime lacks MPS bfloat16 support. Restart with --device cpu."
                ) from None
        dtype = torch.float32 if device == "cpu" else torch.bfloat16
        if device == "cuda" and not torch.cuda.is_bf16_supported():
            raise ValueError(
                "This demo requires bfloat16-capable CUDA for Qwen. Use --device cpu otherwise."
            )
        self.model = (
            AutoModelForCausalLM.from_pretrained(
                str(path),
                local_files_only=True,
                trust_remote_code=False,
                use_safetensors=True,
                dtype=dtype,
                attn_implementation="eager",
            )
            .to(device)
            .eval()
        )
        self.lock = Lock()
        torch.set_num_threads(1)
        # Publisher defaults include sampling settings; this demo uses greedy decoding.
        self.model.generation_config.temperature = None
        self.model.generation_config.top_p = None
        self.model.generation_config.top_k = None

    def generate(
        self, system: str, user: str, max_new_tokens: int = MAX_NEW_TOKENS
    ) -> dict:
        messages = chat_messages(system, user)
        rendered = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self.tokenizer(rendered, return_tensors="pt", add_special_tokens=False)
        prompt_tokens = int(inputs.input_ids.shape[1])
        if prompt_tokens > MAX_CONTEXT_TOKENS:
            raise ValueError(
                "Context exceeds the local prompt budget; no silent truncation was applied"
            )
        inputs = inputs.to(self.device)
        started = time.perf_counter()
        with self.lock, torch.inference_mode():
            torch.manual_seed(7)
            deadline = Deadline(90)
            output = self.model.generate(
                **inputs,
                max_new_tokens=max(32, min(320, max_new_tokens)),
                do_sample=False,
                pad_token_id=self.tokenizer.eos_token_id,
                stopping_criteria=StoppingCriteriaList([deadline]),
                logits_processor=LogitsProcessorList([FiniteLogits()]),
            )
        generated = output[0][prompt_tokens:]
        return {
            "text": self.tokenizer.decode(generated, skip_special_tokens=True).strip(),
            "prompt_tokens": prompt_tokens,
            "generated_tokens": len(generated),
            "generation_seconds": round(time.perf_counter() - started, 3),
            "model": self.name,
            "model_revision": self.revision,
            "device": self.device,
            "dtype": str(self.model.dtype),
            "hit_output_limit": len(generated) >= max(32, min(320, max_new_tokens)),
            "hit_time_limit": time.monotonic() >= deadline.end,
        }
