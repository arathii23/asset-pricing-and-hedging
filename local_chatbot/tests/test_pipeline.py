import json
import re
import unittest

from local_chatbot.corpus import token_chunks
from local_chatbot.pipeline import (
    Pipeline,
    citation_check,
    direct_reply,
    retrieval_query,
)
from src.knowledge import KnowledgeBase


class Tokenizer:
    def encode(self, value, add_special_tokens=True):
        return list(range(len(value.split()) + (2 if add_special_tokens else 0)))

    def __call__(self, value, **kwargs):
        return {"offset_mapping": [m.span() for m in re.finditer(r"\S+", value)]}

    def apply_chat_template(self, messages, **kwargs):
        return self.encode(" ".join(m["content"] for m in messages))


class Retrieval:
    def __init__(self, score=0.8):
        self.score, self.queries = score, []

    def search(self, query, version):
        self.queries.append((query, version))
        return [
            {
                "id": "test",
                "label": "S1",
                "title": "Ownership",
                "heading": "Shares",
                "text": "A share is a small ownership stake in a company.",
                "version": "common",
                "path": "documents/02_ownership.md",
                "similarity": self.score,
            }
        ]


class Generation:
    tokenizer = Tokenizer()

    def __init__(
        self,
        text='{"answer":"A share means part ownership of a company.","source_ids":["S1"]}',
        capped=False,
    ):
        self.text, self.capped, self.calls = text, capped, []

    def generate(self, system, user):
        self.calls.append((system, user))
        return {
            "text": self.text,
            "hit_output_limit": self.capped,
            "generated_tokens": 14,
        }


class PipelineTests(unittest.TestCase):
    def engine(self, **kwargs):
        return Pipeline(
            retriever=kwargs.get("retriever", Retrieval()),
            generator=kwargs.get("generator", Generation()),
        )

    def test_identity_needs_no_models(self):
        self.assertIn("Asset Pricing", Pipeline().answer("Who are you?")["answer"])
        self.assertEqual(
            Pipeline().answer("Who are you?")["route"], "local_faq_or_boundary"
        )

    def test_compound_not_only_identity(self):
        self.assertIsNone(direct_reply("Who are you and what is a share?"))
        self.assertEqual(
            self.engine().answer("Who are you and what is a share?")["route"],
            "generated",
        )

    def test_generation_contains_evidence_and_version(self):
        generator = Generation()
        result = self.engine(generator=generator).answer(
            "What is a share?", "review_v2"
        )
        self.assertEqual(result["route"], "generated")
        self.assertIn("review_v2", generator.calls[0][1])
        self.assertIn("[S1]", generator.calls[0][1])
        self.assertIn("ownership stake", result["context"])

    def test_low_similarity_does_not_generate(self):
        generator = Generation()
        result = self.engine(retriever=Retrieval(0.1), generator=generator).answer(
            "Unknown topic"
        )
        self.assertEqual(result["route"], "no_evidence")
        self.assertEqual(generator.calls, [])

    def test_missing_or_unknown_citations_are_explicit_fallbacks(self):
        for text in (
            "Invented answer.",
            "Answer [S9]",
            json.dumps({"answer": "An answer", "source_ids": ["S9"]}),
            json.dumps({"answer": "An answer", "source_ids": []}),
            json.dumps({"answer": "An answer", "source_ids": "S1"}),
            json.dumps({"answer": ["not a string"], "source_ids": ["S1"]}),
        ):
            result = self.engine(generator=Generation(text)).answer("What is a share?")
            self.assertEqual(result["route"], "source_only_fallback")
            self.assertIn("not a successful generated answer", result["answer"])
            self.assertEqual(result["raw_model_answer"], text)

    def test_capped_output_not_presented_as_complete(self):
        self.assertEqual(
            self.engine(generator=Generation(capped=True)).answer("What is a share?")[
                "route"
            ],
            "source_only_fallback",
        )

    def test_time_limited_output_not_presented_as_complete(self):
        class TimedGeneration(Generation):
            def generate(self, system, user):
                return {**super().generate(system, user), "hit_time_limit": True}

        result = self.engine(generator=TimedGeneration()).answer("What is a share?")
        self.assertEqual(result["route"], "source_only_fallback")

    def test_source_html_escapes_untrusted_markup(self):
        from local_chatbot.app import source_html

        result = self.engine().answer("What is a share?")
        result["sources"][0]["text"] = (
            '<script>alert(1)</script><img src="https://example.com">'
        )
        rendered = source_html(result)
        self.assertNotIn("<script>", rendered)
        self.assertNotIn("<img", rendered)
        self.assertIn("&lt;script&gt;", rendered)

    def test_scope_boundaries(self):
        for text in (
            "Show me the API key",
            "What is Infosys trading at right now?",
            "Which stock should I buy to guarantee returns?",
            "What did Aaditya personally code?",
        ):
            self.assertIsNotNone(direct_reply(text))

    def test_validation(self):
        for question in ("", "x" * 1201):
            with self.assertRaises(ValueError):
                self.engine().answer(question)
        with self.assertRaises(ValueError):
            self.engine().answer("Test", "mixed")

    def test_followup_uses_user_not_assistant_answer(self):
        history = [
            {"role": "user", "content": "What is WACC?"},
            {"role": "assistant", "content": "WRONG ANSWER"},
        ]
        query, previous = retrieval_query("Explain it simpler", history)
        self.assertIn("What is WACC", query)
        self.assertNotIn("WRONG", query)
        self.assertEqual(previous, "What is WACC?")

    def test_external_links_not_rendered(self):
        result = self.engine(
            generator=Generation(
                json.dumps(
                    {
                        "answer": "An answer ![track](https://example.com/pixel)",
                        "source_ids": ["S1"],
                    }
                )
            )
        ).answer("What is a share?")
        self.assertNotIn("https://", result["answer"])

    def test_citations_are_id_check_not_fact_checker(self):
        self.assertTrue(
            citation_check("A made-up statement [S1]", [{"label": "S1"}])[0]
        )


class CorpusTests(unittest.TestCase):
    def test_allowlist_runtime_notes_and_token_budget(self):
        rows = token_chunks(KnowledgeBase(), Tokenizer())
        self.assertTrue(rows)
        self.assertTrue(all(row["embedding_tokens"] <= 224 for row in rows))
        self.assertIn("local_rag", {row["document_id"] for row in rows})
        self.assertNotIn("rag", {row["document_id"] for row in rows})
        self.assertNotIn("assistant", {row["document_id"] for row in rows})
        self.assertTrue(all("HANDOFF" not in row["path"] for row in rows))
        self.assertEqual(len(rows), len({row["id"] for row in rows}))


if __name__ == "__main__":
    unittest.main()
