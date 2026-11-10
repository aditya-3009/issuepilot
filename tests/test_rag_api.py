from fastapi.testclient import TestClient

from issuepilot.main import app
import issuepilot.main as main_module

client = TestClient(app)


def test_ask_returns_answer_and_source_links(monkeypatch):
    retrieved = [{
        "repo": "fastapi/fastapi", "number": 123,
        "title": "Validation response is inconsistent", "state": "closed",
        "url": "https://github.com/fastapi/fastapi/issues/123",
        "similarity": 0.82, "body": "Unexpected validation response.",
    }]
    monkeypatch.setattr(main_module, "semantic_search", lambda q, top_k=5: retrieved)
    monkeypatch.setattr(main_module, "generate_answer", lambda q, items: "Evidence-based answer.")

    response = client.post("/issues/ask", json={"question": "Why is validation inconsistent?", "top_k": 1})
    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "Evidence-based answer."
    assert payload["sources"][0]["url"] == "https://github.com/fastapi/fastapi/issues/123"


def test_ask_returns_no_evidence_without_calling_llm(monkeypatch):
    monkeypatch.setattr(main_module, "semantic_search", lambda q, top_k=5: [])
    def should_not_run(*args, **kwargs):
        raise AssertionError("LLM should not be called when retrieval is empty")
    monkeypatch.setattr(main_module, "generate_answer", should_not_run)

    response = client.post("/issues/ask", json={"question": "Explain this issue"})
    assert response.status_code == 200
    assert response.json()["sources"] == []
    assert "could not find relevant issues" in response.json()["answer"]


def test_ask_reports_missing_llm_configuration(monkeypatch):
    from issuepilot.answering import LLMConfigurationError
    monkeypatch.setattr(main_module, "semantic_search", lambda q, top_k=5: [{"repo":"a/b","number":1,"title":"Example","url":"https://github.com/a/b/issues/1","similarity":0.9}])
    def unconfigured(*args, **kwargs):
        raise LLMConfigurationError("Set LLM_API_KEY and LLM_MODEL.")
    monkeypatch.setattr(main_module, "generate_answer", unconfigured)
    response = client.post("/issues/ask", json={"question": "Explain this issue"})
    assert response.status_code == 503
