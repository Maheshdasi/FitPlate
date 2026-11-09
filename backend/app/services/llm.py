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
TIMEOUT_S = 45
USER_AGENT = "FitPlate/1.0 (+https://github.com/Maheshdasi/FitPlate)"


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


def short_reason(err: Exception) -> str:
    """A one-line, key-free explanation of why the AI call failed, shown under the fallback answer."""
    text = str(err)
    code = text[:3]
    if code == "403" and "1010" in text:
        return "the AI service blocked the request (error 1010)"
    if code == "401" or (code == "403" and "key" in text.lower()):
        return "the API key was rejected (check it in backend/.env)"
    if code == "403":
        return "the AI service refused the request (403); see the backend terminal for details"
    if code == "429":
        return "the free quota is used up for now (try again later)"
    if code == "404":
        return "that AI model isn't available for this key"
    if code.startswith("5"):
        return "the AI service had an error"
    if "No LLM" in text:
        return "no AI key is set"
    if "timed out" in text or "timeout" in text.lower():
        return "the AI service took too long to answer"
    if "Errno" in text or "urlopen" in text or "Name or service" in text:
        return "the backend couldn't reach the internet"
    return "the AI service gave an unexpected answer"


def provider_name(provider: str) -> str:
    return PROVIDERS.get(provider, {}).get("name", provider)


def _post(url: str, body: dict, headers: dict) -> dict:
    # A normal User-Agent: some providers (Groq, behind Cloudflare) refuse Python's default "Python-urllib"
    # with "403 error code: 1010" even when the key is fine.
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "Accept": "application/json",
                                          "User-Agent": USER_AGENT,
                                          **headers})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:  # noqa: S310 (fixed https URLs)
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:300]
        raise LLMError(f"{e.code}: {detail}") from e
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        raise LLMError(str(e)) from e


# ---------------------------------------------------------------- providers
# Preferred Groq chat models, best first. Groq retires models over time, so when the chosen one is gone the
# backend asks Groq which models this key can use and picks the best available one.
GROQ_PREFERRED = ["llama-3.3-70b-versatile", "openai/gpt-oss-120b", "moonshotai/kimi-k2-instruct",
                  "meta-llama/llama-4-maverick-17b-128e-instruct", "qwen/qwen3-32b", "openai/gpt-oss-20b",
                  "llama-3.1-8b-instant"]
NOT_CHAT = ("whisper", "guard", "tts", "playai", "orpheus", "distil", "prompt", "safeguard", "compound")
_groq_model_cache: dict[str, str] = {}


def _get(url: str, headers: dict) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": USER_AGENT, **headers})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:  # noqa: S310 (fixed https URLs)
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise LLMError(f"{e.code}: {e.read().decode(errors='replace')[:300]}") from e
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        raise LLMError(str(e)) from e


def pick_groq_model(available: list[str]) -> str | None:
    """The best chat model from the ones a key can use."""
    for name in GROQ_PREFERRED:
        if name in available:
            return name
    chat = [m for m in available if not any(w in m.lower() for w in NOT_CHAT)]
    return max(chat, key=lambda m: ("70b" in m or "120b" in m, "llama" in m, m)) if chat else None


def _groq(key, model, system, messages):
    base = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    headers = {"Authorization": f"Bearer {key}"}
    model = _groq_model_cache.get(key, model)

    def call(name):
        data = _post(base + "/chat/completions", {"model": name, "temperature": 0.5, "max_tokens": 900,
                                                  "messages": [{"role": "system", "content": system}, *messages]},
                     headers)
        return data["choices"][0]["message"]["content"], []

    try:
        return call(model)
    except LLMError as e:
        text = str(e)
        if not (text.startswith("404") or "model_not_found" in text or "decommissioned" in text
                or "does not exist" in text):
            raise
        available = [m["id"] for m in _get(base + "/models", headers).get("data", []) if m.get("active", True)]
        better = pick_groq_model([m for m in available if m != model])
        if not better:
            raise
        logger.info("Groq model %s is not available, using %s", model, better)
        _groq_model_cache[key] = better
        return call(better)


GEMINI_FALLBACK_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash"]


def _gemini(key, model, system, messages):
    """Gemini, with Google Search when allowed. Falls back to other model names and the other way of sending the key,
    so a model that was renamed or a key type that only works one way still gets an answer."""
    base = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta")
    contents = [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
                for m in messages]
    body = {"systemInstruction": {"parts": [{"text": system}]}, "contents": contents,
            "generationConfig": {"temperature": 0.5, "maxOutputTokens": 4096}}
    auth_ways = [({"x-goog-api-key": key}, ""), ({}, f"?key={key}")]
    last: LLMError | None = None
    for name in dict.fromkeys([model, *GEMINI_FALLBACK_MODELS]):
        for headers, query in auth_ways:
            url = f"{base}/models/{name}:generateContent{query}"
            for with_search in (True, False):
                try:
                    data = _post(url, {**body, "tools": [{"google_search": {}}]} if with_search else body, headers)
                    text, sources = _gemini_parse(data)
                    if text.strip():
                        return text, sources
                    last = LLMError(f"empty answer from {name}")
                except LLMError as e:
                    last = e
                    code = str(e)[:3]
                    if code in ("401", "403") and not with_search:
                        break           # key rejected this way: try the other way of sending it
                    if code == "404":
                        break           # unknown model: try the next model name
                    if code not in ("400", "401", "403", "429") and not code.startswith("5"):
                        raise           # network problem: no point retrying here
            if last and str(last)[:3] == "404":
                break
    raise last or LLMError("Gemini gave no answer")


def _gemini_parse(data):
    cand = (data.get("candidates") or [{}])[0]
    text = "".join(p.get("text", "") for p in (cand.get("content") or {}).get("parts", []) if not p.get("thought"))
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
