"""Minimal Vertex Gemini client (google-genai SDK, toms-gym service account, global location)."""
import json
import os
import time

os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS",
                      "/Users/toka/code/toms_gym/backend/credentials.json")

from google import genai  # noqa: E402
from google.genai import types  # noqa: E402

PROJECT = "toms-gym"
LOCATION = "global"

_client = None


def client():
    global _client
    if _client is None:
        _client = genai.Client(vertexai=True, project=PROJECT, location=LOCATION)
    return _client


def generate(model, parts, temperature=0.0, json_mode=True, retries=3, thinking=None):
    """parts: list of {"text": ...} or {"inline_data": {"mime_type", "data"}} (data = base64)."""
    import base64
    sdk_parts = []
    for p in parts:
        if "text" in p:
            sdk_parts.append(types.Part.from_text(text=p["text"]))
        else:
            sdk_parts.append(types.Part.from_bytes(
                data=base64.b64decode(p["inline_data"]["data"]),
                mime_type=p["inline_data"]["mime_type"]))
    cfg = {"temperature": temperature}
    if json_mode:
        cfg["response_mime_type"] = "application/json"
    if thinking is not None:
        cfg["thinking_config"] = types.ThinkingConfig(thinking_budget=thinking)
    last = None
    for attempt in range(retries):
        try:
            r = client().models.generate_content(
                model=model, contents=[types.Content(role="user", parts=sdk_parts)],
                config=types.GenerateContentConfig(**cfg))
            usage = {}
            if r.usage_metadata:
                usage = {"totalTokenCount": r.usage_metadata.total_token_count,
                         "promptTokenCount": r.usage_metadata.prompt_token_count}
            return (r.text or ""), usage
        except Exception as e:  # noqa: BLE001
            last = str(e)[:300]
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"gemini {model} failed: {last}")


def parse_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text)
