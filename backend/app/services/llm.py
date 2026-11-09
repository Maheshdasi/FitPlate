"""Large language model (LLM) answers for the assistant.

The assistant can answer any question (fitness, food, cooking, general knowledge) through a hosted LLM,
grounded in the user's own FitPlate data. Three providers are supported; set one API key in backend/.env:

    GROQ_API_KEY       free, no card needed (https://console.groq.com/keys)   default model: llama-3.3-70b-versatile
    GEMINI_API_KEY     free with a Google account (https://aistudio.google.com/apikey); can search Google
    ANTHROPIC_API_KEY  Claude (https://console.anthropic.com)

Optional: LLM_PROVIDER (groq / gemini / anthropic) to choose when several keys are set, LLM_MODEL to change the model.
With no key, or if the provider fails, the assistant falls back to the offline ML assistant.
Only the standard library is used for HTTP, so no extra packages are needed.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field

logger = logging.getLogger("fitness.llm")

PROVIDERS = {
    "groq": {"env": "GROQ_API_KEY", "model": "llama-3.3-70b-versatile", "name": "Llama (Groq)"},
    "gemini": {"env": "GEMINI_API_KEY", "model": "gemini-flash-latest", "name": "Gemini"},
    "anthropic": {"env": "ANTHROPIC_API_KEY", "model": "claude-haiku-4-5", "name": "Claude"},
}
TIMEOUT_S = 30


class LLMError(Exception):
    pass


@dataclass
class LLMAnswer:
    text: str
    provider: str
    model: str
    sources: list[dict] = field(default_factory=list)  # [{title, url}] when the model searched the web


def configured() -> tuple[str, str, str] | None:
    """(provider, api_key, model) from the environment, or None when no key is set."""
    wanted = os.getenv("LLM_PROVIDER", "").strip().lower()
    order = [wanted] if wanted in PROVIDERS else list(PROVIDERS)
    for p in order:
        key = os.getenv(PROVIDERS[p]["env"], "").strip()
        if key:
            return p, key, os.getenv("LLM_MODEL", "").strip() or PROVIDERS[p]["model"]
    return None


def provider_name(provider: str) -> str:
    return PROVIDERS.get(provider, {}).get("name", provider)


def _post(url: str, body: dict, headers: dict) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:  # noqa: S310 (fixed https URLs)
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:300]
        raise LLMError(f"{e.code}: {detail}") from e
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        raise LLMError(str(e)) from e


# ---------------------------------------------------------------- providers
def _groq(key, model, system, messages):
    url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1") + "/chat/completions"
    data = _post(url, {"model": model, "temperature": 0.5, "max_tokens": 900,
                       "messages": [{"role": "system", "content": system}, *messages]},
                 {"Authorization": f"Bearer {key}"})
    return data["choices"][0]["message"]["content"], []


def _gemini(key, model, system, messages):
    base = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta")
    url = f"{base}/models/{model}:generateContent"
    contents = [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
                for m in messages]
    body = {"systemInstruction": {"parts": [{"text": system}]}, "contents": contents,
            "generationConfig": {"temperature": 0.5, "maxOutputTokens": 1200}}
    headers = {"x-goog-api-key": key}
    try:
        # Let Gemini search Google for current facts; retry without it if the model or plan doesn't allow it
        data = _post(url, {**body, "tools": [{"google_search": {}}]}, headers)
    except LLMError as e:
        if not str(e).startswith(("400", "403", "429")):
            raise
        data = _post(url, body, headers)
    cand = data["candidates"][0]
    text = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []))
    sources = []
    for chunk in (cand.get("groundingMetadata") or {}).get("groundingChunks", []) or []:
        web = chunk.get("web") or {}
        if web.get("uri") and len(sources) < 4:
            sources.append({"title": web.get("title") or web["uri"], "url": web["uri"]})
    return text, sources


def _anthropic(key, model, system, messages):
    url = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1") + "/messages"
    data = _post(url, {"model": model, "max_tokens": 900, "system": system, "messages": messages},
                 {"x-api-key": key, "anthropic-version": "2023-06-01"})
    return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"), []


CALLS = {"groq": _groq, "gemini": _gemini, "anthropic": _anthropic}


def ask(system: str, messages: list[dict]) -> LLMAnswer:
    """Send the conversation to the configured provider. Raises LLMError if none is set or the call fails."""
    cfg = configured()
    if cfg is None:
        raise LLMError("No LLM API key configured")
    provider, key, model = cfg
    try:
        text, sources = CALLS[provider](key, model, system, normalise(messages))
    except (KeyError, IndexError, TypeError) as e:
        raise LLMError(f"Unexpected response from {provider}: {e}") from e
    text = clean(text)
    if not text:
        raise LLMError(f"Empty answer from {provider}")
    return LLMAnswer(text=text, provider=provider, model=model, sources=sources)


def normalise(messages: list[dict]) -> list[dict]:
    """Start with a user turn and alternate roles (merging repeats), as every provider expects."""
    out: list[dict] = []
    for m in messages:
        if not m.get("content", "").strip() or (not out and m["role"] != "user"):
            continue
        if out and out[-1]["role"] == m["role"]:
            out[-1] = {"role": m["role"], "content": out[-1]["content"] + "\n\n" + m["content"]}
        else:
            out.append({"role": m["role"], "content": m["content"]})
    return out


def clean(text: str) -> str:
    """Keep answers in the app's plain style: no em or en dashes, no markdown headings or tables."""
    text = (text or "").strip()
    text = text.replace(" \u2014 ", ", ").replace("\u2014", ", ").replace(" \u2013 ", " to ").replace("\u2013", " to ")
    lines = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("#"):
            line = "**" + s.lstrip("#").strip() + "**"
        if s.startswith("|") or set(s) <= {"-", "|", ":", " "} and s.count("-") > 2:
            continue
        lines.append(line.rstrip())
    return "\n".join(lines).strip()


# ---------------------------------------------------------------- prompt
SYSTEM_PROMPT = """You are the FitPlate assistant, a friendly and knowledgeable AI inside the FitPlate fitness and \
nutrition app. Answer whatever the user asks, the way a good search engine and a smart assistant would: fitness, \
nutrition, recipes, cooking, sleep, habits, and general knowledge questions too. Be accurate and specific.

When the question is about the user's own day, targets, food or workouts, use THEIR DATA below and be precise with \
the numbers. Respect their diet type and allergies in every food suggestion, and never suggest anything they are \
allergic to. Prefer meals from the app's suggestions when they fit, and Indian foods are welcome. If they say they \
don't have an ingredient, suggest something without it.

Style: warm and direct. Usually under 170 words unless they ask for detail. Plain text with short paragraphs; use \
"- " bullet points for lists and **bold** for key items. No headings, no tables, no emojis, and never use em dashes \
or en dashes. Use metric units (kcal, g, kg, ml) unless asked otherwise.

Safety: you are not a doctor. For medical conditions, symptoms, injuries, pregnancy or medicines, give general, \
well-established information only, never a diagnosis, treatment plan or medicine dose, and suggest seeing a doctor \
or registered dietitian. Don't recommend crash diets, eating under about 1200 kcal a day, or unsafe training. If \
you don't know something or it needs very recent information you can't check, say so honestly."""


def build_system_prompt(data: dict) -> str:
    return SYSTEM_PROMPT + "\n\nTHEIR DATA (from FitPlate, today):\n" + json.dumps(data, ensure_ascii=False, indent=1)
