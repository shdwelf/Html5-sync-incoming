"""Step 4b — send the packet to an LLM and post-validate what comes back.

Providers (standard library ``urllib`` only, no SDKs):

``openai``     any OpenAI-compatible ``/v1/chat/completions`` endpoint —
               OpenAI itself, Azure-style gateways, LM Studio, vLLM, llama.cpp,
               and Ollama (``--base-url http://localhost:11434/v1``).
               Env: ``OPENAI_API_KEY``, ``OPENAI_BASE_URL``.
``anthropic``  the Anthropic Messages API.  Env: ``ANTHROPIC_API_KEY``.

The model's JSON is parsed defensively (fences stripped, first ``{...}``
block taken), then every returned haiku is re-checked locally: syllables are
recounted with :mod:`syllables`, source line ids are resolved against the
packet, and the result records whether the model's count and ours agree.
Nothing the model says is trusted without that cross-check.

``transport`` can be injected for tests or for routing through a proxy: it is
a callable ``(url, headers, body_bytes, timeout) -> response_text``.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from . import TOOL_NAME, __version__
from .packet import Packet, read_packet
from .prompt import SYSTEM_PROMPT, USER_PREAMBLE
from .syllables import backend_name, count_line, explain_line

Transport = Callable[[str, Dict[str, str], bytes, float], str]

DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-sonnet-4-20250514",
}
DEFAULT_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com",
}


class LLMError(RuntimeError):
    pass


def _urllib_transport(url: str, headers: Dict[str, str], body: bytes, timeout: float) -> str:
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    last_err: Optional[Exception] = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:2000]
            if exc.code in (408, 409, 429, 500, 502, 503, 504) and attempt < 3:
                time.sleep(2 ** attempt)
                last_err = LLMError(f"HTTP {exc.code}: {detail}")
                continue
            raise LLMError(f"HTTP {exc.code} from {url}: {detail}") from exc
        except urllib.error.URLError as exc:
            if attempt < 3:
                time.sleep(2 ** attempt)
                last_err = exc
                continue
            raise LLMError(f"cannot reach {url}: {exc.reason}") from exc
    raise LLMError(str(last_err))


class LLMClient:
    def __init__(
        self,
        provider: str = "openai",
        *,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 180.0,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        json_mode: bool = False,
        transport: Optional[Transport] = None,
    ) -> None:
        if provider not in DEFAULT_MODELS:
            raise LLMError(f"unknown provider {provider!r}; use one of {', '.join(DEFAULT_MODELS)}")
        self.provider = provider
        self.model = model or os.environ.get("JOURNAL_LLM_MODEL") or DEFAULT_MODELS[provider]
        env_key = "OPENAI_API_KEY" if provider == "openai" else "ANTHROPIC_API_KEY"
        self.api_key = api_key or os.environ.get(env_key)
        env_base = os.environ.get("OPENAI_BASE_URL") if provider == "openai" else None
        self.base_url = (base_url or env_base or DEFAULT_BASE_URLS[provider]).rstrip("/")
        self.timeout = timeout
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.json_mode = json_mode
        self.transport = transport or _urllib_transport

    # -- request building ---------------------------------------------------
    def build_request(self, system: str, user: str) -> Dict[str, Any]:
        if self.provider == "openai":
            body: Dict[str, Any] = {
                "model": self.model,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            }
            if self.json_mode:
                body["response_format"] = {"type": "json_object"}
            headers = {"Content-Type": "application/json", "User-Agent": f"{TOOL_NAME}/{__version__}"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            return {"url": f"{self.base_url}/chat/completions", "headers": headers, "body": body}
        body = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        headers = {
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
            "User-Agent": f"{TOOL_NAME}/{__version__}",
        }
        if self.api_key:
            headers["x-api-key"] = self.api_key
        return {"url": f"{self.base_url}/v1/messages", "headers": headers, "body": body}

    def complete(self, system: str, user: str) -> str:
        if not self.api_key and "localhost" not in self.base_url and "127.0.0.1" not in self.base_url:
            env = "OPENAI_API_KEY" if self.provider == "openai" else "ANTHROPIC_API_KEY"
            raise LLMError(f"no API key: set ${env} or pass --api-key (local servers need none)")
        req = self.build_request(system, user)
        raw = self.transport(req["url"], req["headers"], json.dumps(req["body"]).encode("utf-8"), self.timeout)
        return self.extract_text(raw)

    def extract_text(self, raw: str) -> str:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise LLMError(f"non-JSON response from {self.provider}: {raw[:300]}") from exc
        if self.provider == "openai":
            try:
                return data["choices"][0]["message"]["content"] or ""
            except (KeyError, IndexError, TypeError) as exc:
                raise LLMError(f"unexpected OpenAI response shape: {raw[:300]}") from exc
        try:
            return "".join(part.get("text", "") for part in data["content"] if part.get("type") == "text")
        except (KeyError, TypeError) as exc:
            raise LLMError(f"unexpected Anthropic response shape: {raw[:300]}") from exc


# --------------------------------------------------------------------------- #
# parsing + validation
# --------------------------------------------------------------------------- #
_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.I | re.M)


def parse_model_json(text: str) -> Dict[str, Any]:
    cleaned = _FENCE_RE.sub("", text.strip())
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start < 0 or end <= start:
            raise LLMError(f"model did not return JSON: {text[:300]!r}")
        data = json.loads(cleaned[start:end + 1])
    if not isinstance(data, dict):
        raise LLMError("model JSON is not an object")
    data.setdefault("haikus", [])
    data.setdefault("excluded", [])
    if not isinstance(data["haikus"], list):
        raise LLMError('"haikus" is not a list')
    return data


def validate_haiku(item: Dict[str, Any], packet: Packet, idx: int) -> Dict[str, Any]:
    by_id = packet.line_by_id()
    lines = [str(x) for x in (item.get("lines") or [])][:3]
    ids = [str(x) for x in (item.get("source_line_ids") or [])]
    resolved = [by_id.get(i) for i in ids]
    unresolved = [i for i, ln in zip(ids, resolved) if ln is None]
    src_lines = [ln for ln in resolved if ln is not None]

    local_counts: List[int] = []
    ranges: List[List[int]] = []
    explanations: List[str] = []
    for ln in lines:
        (lo, hi), _ = count_line(ln)
        ranges.append([lo, hi])
        explanations.append(explain_line(ln))
        local_counts.append(lo if lo == hi else lo)
    devs = [0 if lo <= t <= hi else min(abs(lo - t), abs(hi - t)) for (lo, hi), t in zip(ranges, (5, 7, 5))]
    total = sum(devs) if len(devs) == 3 else None
    if len(lines) != 3:
        local_validation = f"not 3 lines ({len(lines)})"
    elif total == 0:
        local_validation = "exact"
    elif total is not None and total <= 2 and max(devs) <= 1:
        local_validation = f"approximate (off by {total})"
    else:
        local_validation = "not 5-7-5"

    model_counts = item.get("syllables")
    agree = None
    if isinstance(model_counts, list) and len(model_counts) == 3 and len(ranges) == 3:
        try:
            agree = all(lo <= int(m) <= hi for m, (lo, hi) in zip(model_counts, ranges))
        except (TypeError, ValueError):
            agree = None

    ocr_lines = [str(x) for x in (item.get("ocr_lines") or [])]
    corrections = [{"ocr": o, "model": m} for o, m in zip(ocr_lines, lines) if o.strip() != m.strip()]
    if not ocr_lines and src_lines:
        corrections = [{"ocr": ln.text, "model": m} for ln, m in zip(src_lines, lines) if ln.text.strip() != m.strip()]

    boxes = [ln.bbox for ln in src_lines if ln.bbox]
    confs = [ln.conf for ln in src_lines if ln.conf is not None]
    return {
        "id": f"haiku_{idx}",
        "form": item.get("pattern") or ("5-7-5" if local_validation == "exact" else "unspecified"),
        "lines": lines,
        "syllables": model_counts,
        "syllable_validation_model": item.get("syllable_validation"),
        "local_syllables": local_counts,
        "local_syllable_ranges": ranges,
        "local_validation": local_validation,
        "local_explanation": explanations,
        "model_local_agree": agree,
        "confidence": item.get("confidence"),
        "notes": item.get("notes"),
        "ocr_corrections": corrections,
        "source": {
            "page": item.get("page") or (src_lines[0].page if src_lines else None),
            "line_ids": ids,
            "unresolved_line_ids": unresolved,
            "line_numbers": [ln.n for ln in src_lines],
            "bbox": [min(b[0] for b in boxes), min(b[1] for b in boxes),
                     max(b[2] for b in boxes), max(b[3] for b in boxes)] if boxes else None,
            "ocr_text": [ln.text for ln in src_lines],
            "ocr_confidence": round(sum(confs) / len(confs), 1) if confs else None,
        },
    }


def build_user_message(packet: Packet) -> str:
    return USER_PREAMBLE + packet.xml_text


def extract_with_llm(
    packet: Packet,
    client: LLMClient,
    *,
    system_prompt: str = SYSTEM_PROMPT,
    dry_run: bool = False,
) -> Dict[str, Any]:
    user = build_user_message(packet)
    request = client.build_request(system_prompt, user)
    result: Dict[str, Any] = {
        "schema": f"{TOOL_NAME}/haikus/1.0",
        "generated": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "engine": {
            "name": "llm",
            "tool": f"{TOOL_NAME}/{__version__}",
            "provider": client.provider,
            "model": client.model,
            "endpoint": request["url"],
            "local_syllables": backend_name(),
        },
        "packet": packet.path,
        "preservation": {k: v.get("text") for k, v in packet.preservation.items()
                         if k in ("xena_file", "master_file", "original_file", "input_source_uri")},
    }
    if dry_run:
        result["dry_run"] = True
        result["request"] = {"url": request["url"], "body": request["body"]}
        result["haikus"] = []
        return result

    raw_text = client.complete(system_prompt, user)
    data = parse_model_json(raw_text)
    result["haikus"] = [validate_haiku(item, packet, i + 1) for i, item in enumerate(data["haikus"])
                        if isinstance(item, dict)]
    result["excluded_by_model"] = data.get("excluded") or []
    result["raw_response"] = raw_text
    result["stats"] = {
        "haikus": len(result["haikus"]),
        "local_exact": sum(1 for h in result["haikus"] if h["local_validation"] == "exact"),
        "model_local_agree": sum(1 for h in result["haikus"] if h["model_local_agree"]),
    }
    return result


def extract_from_file(packet_path: str, client: LLMClient, **kw: Any) -> Dict[str, Any]:
    return extract_with_llm(read_packet(packet_path), client, **kw)


def render_prompt(packet: Packet, system_prompt: str = SYSTEM_PROMPT) -> str:
    """Everything to paste into a chat UI by hand: system prompt, then the packet."""
    return (
        "=== SYSTEM PROMPT ===\n" + system_prompt.rstrip() + "\n\n"
        "=== USER MESSAGE ===\n" + build_user_message(packet)
    )
