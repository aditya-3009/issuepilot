import pytest

from issuepilot.answering import LLMConfigurationError, LLMRequestError, generate_answer


def _issues():
    return [{
        "repo": "fastapi/fastapi", "number": 123,
        "title": "Validation response is inconsistent", "state": "closed",
        "url": "https://github.com/fastapi/fastapi/issues/123",
        "similarity": 0.82, "body": "Unexpected validation response.",
    }]


def test_generate_answer_calls_openai_compatible_endpoint(monkeypatch):
    import issuepilot.answering as module
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.setenv("LLM_BASE_URL", "https://llm.example/v1")

    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return {"choices": [{"message": {"content": "Evidence-based answer."}}]}

    captured = {}
    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs
        return Response()
    monkeypatch.setattr(module.requests, "post", fake_post)

    result = generate_answer("Why is validation inconsistent?", _issues())
    assert result == "Evidence-based answer."
    assert captured["url"] == "https://llm.example/v1/chat/completions"
    assert captured["kwargs"]["headers"]["Authorization"] == "Bearer test-key"
    assert captured["kwargs"]["json"]["model"] == "test-model"
    assert "untrusted data" in captured["kwargs"]["json"]["messages"][0]["content"]


def test_generate_answer_requires_configuration(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    with pytest.raises(LLMConfigurationError):
        generate_answer("Question?", _issues())


def test_generate_answer_wraps_provider_timeout(monkeypatch):
    import issuepilot.answering as module
    import requests
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    def fake_post(*args, **kwargs):
        raise requests.Timeout("timed out")
    monkeypatch.setattr(module.requests, "post", fake_post)
    with pytest.raises(LLMRequestError):
        generate_answer("Question?", _issues())


def test_generate_answer_rejects_empty_provider_response(monkeypatch):
    import issuepilot.answering as module
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL", "test-model")

    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return {"choices": [{"message": {"content": " "}}]}

    monkeypatch.setattr(module.requests, "post", lambda *args, **kwargs: Response())
    with pytest.raises(LLMRequestError):
        generate_answer("Question?", _issues())
