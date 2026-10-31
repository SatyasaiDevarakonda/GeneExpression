"""Thin Gemini HTTP client (embeddings + chat, with streaming and tool calling).
Exposes the same shape chat.py/build_index.py expect from an LLM client: api_key/available/embed/chat/chat_stream.
The API key is read from the environment only."""
import json
import os
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

BASE = "https://generativelanguage.googleapis.com/v1beta"
EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-001")
CHAT_MODEL = os.getenv("GEMINI_CHAT_MODEL", "gemini-2.5-flash")


def api_key() -> str | None:
    k = os.getenv("GEMINI_API_KEY", "").strip()
    return k or None


def available() -> bool:
    return api_key() is not None


def _headers():
    return {"x-goog-api-key": api_key(), "Content-Type": "application/json"}


def _post_with_retry(client: httpx.Client, url: str, json_body: dict, retries: int = 5):
    """Gemini's free tier rate-limits aggressively; back off on 429 instead of failing the whole batch."""
    delay = 2.0
    for attempt in range(retries):
        r = client.post(url, headers=_headers(), json=json_body)
        if r.status_code not in (429, 503) or attempt == retries - 1:
            r.raise_for_status()
            return r
        time.sleep(delay)
        delay *= 2


def embed(texts: list[str]) -> list[list[float]]:
    out = []
    with httpx.Client(timeout=60) as c:
        for t in texts:
            r = _post_with_retry(c, f"{BASE}/models/{EMBED_MODEL}:embedContent",
                                  {"model": f"models/{EMBED_MODEL}", "content": {"parts": [{"text": t[:6000]}]}})
            out.append(r.json()["embedding"]["values"])
    return out


def _to_gemini(messages, tools=None):
    """OpenAI-shaped messages/tools -> Gemini {systemInstruction, contents, tools}."""
    system, contents = None, []
    for m in messages:
        role = m["role"]
        if role == "system":
            system = m["content"]
        elif role in ("user",):
            contents.append({"role": "user", "parts": [{"text": m["content"]}]})
        elif role == "assistant":
            calls = m.get("tool_calls")
            if calls:
                parts = []
                for call in calls:
                    fn = call["function"]
                    try:
                        args = json.loads(fn.get("arguments") or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    parts.append({"functionCall": {"name": fn["name"], "args": args}})
                contents.append({"role": "model", "parts": parts})
            else:
                contents.append({"role": "model", "parts": [{"text": m.get("content") or ""}]})
        elif role == "tool":
            try:
                resp = json.loads(m["content"])
            except (json.JSONDecodeError, TypeError):
                resp = {"content": m["content"]}
            part = {"functionResponse": {"name": m["name"], "response": resp}}
            if contents and contents[-1]["role"] == "user" and all("functionResponse" in p for p in contents[-1]["parts"]):
                contents[-1]["parts"].append(part)
            else:
                contents.append({"role": "user", "parts": [part]})

    gemini_tools = None
    if tools:
        decls = [{"name": t["function"]["name"], "description": t["function"]["description"],
                  "parameters": t["function"]["parameters"]} for t in tools]
        gemini_tools = [{"functionDeclarations": decls}]
    return system, contents, gemini_tools


def _message_from_candidate(candidate) -> dict:
    parts = candidate.get("content", {}).get("parts", [])
    text = "".join(p["text"] for p in parts if "text" in p)
    calls = [p["functionCall"] for p in parts if "functionCall" in p]
    out = {"content": text}
    if calls:
        out["tool_calls"] = [{"id": f"call_{i}", "function": {"name": c["name"], "arguments": json.dumps(c.get("args", {}))}}
                              for i, c in enumerate(calls)]
    return out


def chat(messages, tools=None, temperature=0.1, max_tokens=900) -> dict:
    system, contents, gemini_tools = _to_gemini(messages, tools)
    body = {"contents": contents, "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens}}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    if gemini_tools:
        body["tools"] = gemini_tools
    with httpx.Client(timeout=90) as c:
        r = _post_with_retry(c, f"{BASE}/models/{CHAT_MODEL}:generateContent", body)
        return _message_from_candidate(r.json()["candidates"][0])


def chat_stream(messages, temperature=0.1, max_tokens=900):
    """Yields text deltas."""
    system, contents, _ = _to_gemini(messages)
    body = {"contents": contents, "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens}}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    with httpx.Client(timeout=None) as c:
        with c.stream("POST", f"{BASE}/models/{CHAT_MODEL}:streamGenerateContent", params={"alt": "sse"},
                      headers=_headers(), json=body) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if not payload or payload == "[DONE]":
                    continue
                try:
                    parts = json.loads(payload)["candidates"][0].get("content", {}).get("parts", [])
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
                for p in parts:
                    if "text" in p:
                        yield p["text"]
