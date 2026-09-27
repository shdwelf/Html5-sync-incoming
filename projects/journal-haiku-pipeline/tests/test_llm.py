import json
import tempfile
import unittest
from pathlib import Path

from journal_pipeline.hocr import parse_text
from journal_pipeline.llm import LLMClient, LLMError, extract_with_llm, parse_model_json, render_prompt
from journal_pipeline.packet import build_packet, read_packet, write_packet
from journal_pipeline.prompt import SYSTEM_PROMPT

TEXT = ("Tuesday, 14 March 2023\n\nRain on the harbour\nthe gulls argue over scraps\nrny coffee goes cold\n\n"
        "Note to self: buy stamps.\n")


def make_packet():
    with tempfile.TemporaryDirectory() as td:   # read_packet loads everything into memory
        return read_packet(write_packet(build_packet(parse_text(TEXT)), Path(td) / "p.packet.xml"))


class FakeTransport:
    def __init__(self, reply_text, provider="openai"):
        self.calls = []
        if provider == "openai":
            self.raw = json.dumps({"choices": [{"message": {"role": "assistant", "content": reply_text}}]})
        else:
            self.raw = json.dumps({"content": [{"type": "text", "text": reply_text}]})

    def __call__(self, url, headers, body, timeout):
        self.calls.append((url, headers, json.loads(body), timeout))
        return self.raw


MODEL_REPLY = """```json
{"haikus": [{"lines": ["Rain on the harbour", "the gulls argue over scraps", "my coffee goes cold"],
             "ocr_lines": ["Rain on the harbour", "the gulls argue over scraps", "rny coffee goes cold"],
             "syllables": [5, 7, 5], "syllable_validation": "Rain(1) on(1) the(1) harbour(2) = 5; ...",
             "pattern": "5-7-5", "source_line_ids": ["line_1_2", "line_1_3", "line_1_4"], "page": 1,
             "confidence": 0.93, "notes": "corrected rny -> my"}],
 "excluded": [{"line_ids": ["line_1_1"], "reason": "date heading"}]}
```"""


class LLMTests(unittest.TestCase):
    def test_openai_request_and_validation(self):
        packet = make_packet()
        transport = FakeTransport(MODEL_REPLY)
        client = LLMClient("openai", api_key="sk-test", model="test-model", transport=transport, json_mode=True)
        result = extract_with_llm(packet, client)
        url, headers, body, _ = transport.calls[0]
        self.assertEqual(url, "https://api.openai.com/v1/chat/completions")
        self.assertEqual(headers["Authorization"], "Bearer sk-test")
        self.assertEqual(body["model"], "test-model")
        self.assertEqual(body["response_format"], {"type": "json_object"})
        self.assertEqual(body["messages"][0]["content"], SYSTEM_PROMPT)
        self.assertIn("<pipeline_packet", body["messages"][1]["content"])

        self.assertEqual(result["engine"]["name"], "llm")
        h = result["haikus"][0]
        self.assertEqual(h["lines"][2], "my coffee goes cold")
        self.assertEqual(h["local_validation"], "exact")
        self.assertTrue(h["model_local_agree"])
        self.assertEqual(h["ocr_corrections"], [{"ocr": "rny coffee goes cold", "model": "my coffee goes cold"}])
        self.assertEqual(h["source"]["line_numbers"], [2, 3, 4])
        self.assertEqual(h["source"]["unresolved_line_ids"], [])
        self.assertEqual(result["excluded_by_model"][0]["reason"], "date heading")

    def test_anthropic_request_shape(self):
        packet = make_packet()
        transport = FakeTransport(MODEL_REPLY, provider="anthropic")
        client = LLMClient("anthropic", api_key="sk-ant", transport=transport)
        result = extract_with_llm(packet, client)
        url, headers, body, _ = transport.calls[0]
        self.assertEqual(url, "https://api.anthropic.com/v1/messages")
        self.assertEqual(headers["x-api-key"], "sk-ant")
        self.assertEqual(body["system"], SYSTEM_PROMPT)
        self.assertEqual(len(result["haikus"]), 1)

    def test_dry_run_needs_no_key_and_makes_no_call(self):
        packet = make_packet()
        transport = FakeTransport(MODEL_REPLY)
        client = LLMClient("openai", api_key=None, transport=transport)
        client.api_key = None
        result = extract_with_llm(packet, client, dry_run=True)
        self.assertTrue(result["dry_run"])
        self.assertEqual(transport.calls, [])
        self.assertIn("messages", result["request"]["body"])

    def test_missing_key_is_a_clear_error(self):
        packet = make_packet()
        client = LLMClient("openai", api_key=None, transport=FakeTransport(MODEL_REPLY))
        client.api_key = None
        with self.assertRaises(LLMError):
            extract_with_llm(packet, client)
        # local OpenAI-compatible servers (Ollama etc.) need no key
        local = LLMClient("openai", api_key=None, base_url="http://localhost:11434/v1", transport=FakeTransport(MODEL_REPLY))
        local.api_key = None
        self.assertEqual(len(extract_with_llm(packet, local)["haikus"]), 1)

    def test_parse_model_json_variants(self):
        self.assertEqual(parse_model_json('{"haikus": []}')["haikus"], [])
        self.assertEqual(parse_model_json('Sure! Here it is:\n{"haikus": [], "excluded": []}\nHope this helps')["excluded"], [])
        with self.assertRaises(LLMError):
            parse_model_json("no json at all")

    def test_model_disagreement_is_flagged(self):
        packet = make_packet()
        reply = json.dumps({"haikus": [{"lines": ["Rain on the harbour", "the gulls argue over scraps and bread", "my coffee goes cold"],
                                        "syllables": [5, 7, 5], "source_line_ids": ["line_1_2", "line_1_3", "nope"]}]})
        client = LLMClient("openai", api_key="k", transport=FakeTransport(reply))
        h = extract_with_llm(packet, client)["haikus"][0]
        self.assertFalse(h["model_local_agree"])
        self.assertEqual(h["local_syllables"][1], 9)
        self.assertEqual(h["source"]["unresolved_line_ids"], ["nope"])

    def test_render_prompt(self):
        text = render_prompt(make_packet())
        self.assertTrue(text.startswith("=== SYSTEM PROMPT ==="))
        self.assertIn("<ocr_transcript", text)


if __name__ == "__main__":
    unittest.main()
