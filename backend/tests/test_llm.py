"""The LLM assistant, tested against a small fake provider server (no real API key or internet needed)."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from app.services import llm


class FakeProvider(BaseHTTPRequestHandler):
    requests: list = []
    fail = False
    header_key_rejected = False   # like Google AQ. keys that only work as ?key=
    missing_models: tuple = ()     # model names that return 404

    def do_POST(self):  # noqa: N802
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeProvider.requests.append({"path": self.path, "body": body, "headers": dict(self.headers)})
        status = None
        if FakeProvider.fail:
            status = 500
        elif any(f"/models/{m}:" in self.path for m in FakeProvider.missing_models):
            status = 404
        elif FakeProvider.header_key_rejected and "key=" not in self.path:
            status = 401
        if status:
            self.send_response(status)
            self.end_headers()
            self.wfile.write(b'{"error": "nope"}')
            return
        if "generateContent" in self.path:  # Gemini
            answer = "Creatine is safe for most adults \u2014 3 to 5 g a day."
            out = {"candidates": [{"content": {"parts": [{"text": answer}]},
                                   "groundingMetadata": {"groundingChunks": [
                                       {"web": {"uri": "https://example.org/creatine", "title": "Creatine facts"}}]}}]}
        else:  # Groq (OpenAI style)
            reply = "## Dinner idea\nTry **dal and rice** \u2014 it fits your plan."
            out = {"choices": [{"message": {"content": reply}}]}
        data = json.dumps(out).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


@pytest.fixture
def fake_llm(monkeypatch):
    server = HTTPServer(("127.0.0.1", 0), FakeProvider)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}"
    FakeProvider.requests, FakeProvider.fail = [], False
    FakeProvider.header_key_rejected, FakeProvider.missing_models = False, ()
    for k in ("GROQ_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY", "LLM_PROVIDER", "LLM_MODEL"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("GROQ_BASE_URL", base)
    monkeypatch.setenv("GEMINI_BASE_URL", base)
    yield FakeProvider
    server.shutdown()


def test_without_a_key_the_offline_assistant_answers(client, auth, monkeypatch):
    for k in ("GROQ_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    assert client.get("/ai/status", headers=auth).json()["mode"] == "offline"
    r = client.post("/ai/chat", json={"message": "What should I eat for dinner?"}, headers=auth).json()
    assert r["source"] == "offline" and r["intent"] == "meal_suggestion"


def test_llm_answers_with_the_users_data_and_history(client, auth, fake_llm, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    assert client.get("/ai/status", headers=auth).json() == {
        "mode": "llm", "provider": "groq", "name": "Llama (Groq)", "model": "llama-3.3-70b-versatile"}
    history = [{"role": "assistant", "text": "Hi! How can I help?"},
               {"role": "user", "text": "I don't have peanut butter"}, {"role": "assistant", "text": "Noted."}]
    r = client.post("/ai/chat", json={"message": "What can I have for dinner?", "history": history},
                    headers=auth).json()
    assert r["source"] == "groq" and r["intent"] == "llm"
    # Headings become bold lines and em dashes are removed
    assert r["reply"] == "**Dinner idea**\nTry **dal and rice**, it fits your plan."

    sent = fake_llm.requests[-1]
    assert sent["headers"]["Authorization"] == "Bearer test-key"
    assert sent["headers"]["User-Agent"].startswith("FitPlate/")  # not "Python-urllib", which Groq blocks
    msgs = sent["body"]["messages"]
    assert msgs[0]["role"] == "system" and '"peanuts"' in msgs[0]["content"]  # allergies from the profile
    assert '"daily_calories"' in msgs[0]["content"] and "app_meal_suggestions_for_" in msgs[0]["content"]
    # The greeting is dropped so the conversation starts with the user, then roles alternate
    assert [m["role"] for m in msgs[1:]] == ["user", "assistant", "user"]
    assert msgs[-1]["content"] == "What can I have for dinner?"


def test_gemini_returns_web_sources(client, auth, fake_llm, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "g-key")
    r = client.post("/ai/chat", json={"message": "Is creatine safe?"}, headers=auth).json()
    assert r["source"] == "gemini" and "3 to 5 g" in r["reply"] and "\u2014" not in r["reply"]
    assert r["sources"] == [{"title": "Creatine facts", "url": "https://example.org/creatine"}]
    sent = fake_llm.requests[-1]
    assert sent["headers"]["X-Goog-Api-Key"] == "g-key" and sent["body"]["tools"] == [{"google_search": {}}]


def test_provider_failure_falls_back_to_offline(client, auth, fake_llm, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    fake_llm.fail = True
    r = client.post("/ai/chat", json={"message": "How much protein do I need today?"}, headers=auth).json()
    assert r["source"] == "offline" and r["intent"] == "protein_query"
    assert r["llm_error"] == "the AI service had an error"


def test_gemini_retries_other_key_style_and_model_names(client, auth, fake_llm, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "AQ.test")
    fake_llm.header_key_rejected = True
    fake_llm.missing_models = ("gemini-flash-latest",)
    r = client.post("/ai/chat", json={"message": "Is creatine safe?"}, headers=auth).json()
    assert r["source"] == "gemini" and "3 to 5 g" in r["reply"]
    assert "/models/gemini-2.5-flash:generateContent?key=AQ.test" in fake_llm.requests[-1]["path"]


def test_failure_reason_is_explained(client, auth, fake_llm, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "bad")
    fake_llm.missing_models = ("gemini-flash-latest", "gemini-2.5-flash", "gemini-2.0-flash")
    r = client.post("/ai/chat", json={"message": "Is creatine safe?"}, headers=auth).json()
    assert r["source"] == "offline" and r["llm_error"] == "that AI model isn't available for this key"


def test_medicine_questions_never_reach_the_llm(client, auth, fake_llm, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    r = client.post("/ai/chat", json={"message": "What dose of metformin should I take?"}, headers=auth).json()
    assert r["intent"] == "medical_safety" and fake_llm.requests == []


def test_normalise_and_clean():
    msgs = [{"role": "assistant", "content": "hi"}, {"role": "user", "content": "a"},
            {"role": "user", "content": "b"}, {"role": "assistant", "content": " "}]
    assert llm.normalise(msgs) == [{"role": "user", "content": "a\n\nb"}]
    assert llm.clean("| a | b |\n|---|---|\nok \u2013 fine") == "ok to fine"
