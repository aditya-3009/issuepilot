
from unittest.mock import MagicMock, patch

import pytest
import requests

from issuepilot.github_client import GitHubAPIError, fetch_issues


def make_response(status_code, payload=None, headers=None, text=""):
    response = MagicMock()
    response.status_code = status_code
    response.ok = 200 <= status_code < 400
    response.headers = headers or {}
    response.text = text
    response.json.return_value = payload
    return response


def test_fetch_issues_paginates_and_excludes_pull_requests():
    first_page = [
        {"id": 101, "number": 1, "title": "Issue one"},
        {
            "id": 102,
            "number": 2,
            "title": "Pull request",
            "pull_request": {"url": "https://api.github.com/pulls/2"},
        },
    ]
    second_page = [
        {"id": 103, "number": 3, "title": "Issue three"},
    ]

    mock_session = MagicMock()
    mock_session.get.side_effect = [
        make_response(200, first_page),
        make_response(200, second_page),
    ]

    mock_session_context = MagicMock()
    mock_session_context.__enter__.return_value = mock_session

    with patch(
        "issuepilot.github_client.requests.Session",
        return_value=mock_session_context,
    ):
        issues = fetch_issues("owner", "repo", pages=3, per_page=2)

    assert [issue["id"] for issue in issues] == [101, 103]
    assert mock_session.get.call_count == 2

    first_call = mock_session.get.call_args_list[0]
    second_call = mock_session.get.call_args_list[1]

    assert first_call.kwargs["params"]["page"] == 1
    assert second_call.kwargs["params"]["page"] == 2


def test_fetch_issues_rejects_invalid_pagination():
    with pytest.raises(ValueError, match="pages must be at least 1"):
        fetch_issues("owner", "repo", pages=0)

    with pytest.raises(ValueError, match="per_page must be between 1 and 100"):
        fetch_issues("owner", "repo", per_page=101)


def test_fetch_issues_handles_missing_repository():
    mock_session = MagicMock()
    mock_session.get.return_value = make_response(404)

    mock_session_context = MagicMock()
    mock_session_context.__enter__.return_value = mock_session

    with patch(
        "issuepilot.github_client.requests.Session",
        return_value=mock_session_context,
    ):
        with pytest.raises(GitHubAPIError, match="Repository not found"):
            fetch_issues("owner", "missing-repo")


def test_fetch_issues_wraps_network_errors():
    mock_session = MagicMock()
    mock_session.get.side_effect = requests.Timeout("request timed out")

    mock_session_context = MagicMock()
    mock_session_context.__enter__.return_value = mock_session

    with patch(
        "issuepilot.github_client.requests.Session",
        return_value=mock_session_context,
    ):
        with pytest.raises(GitHubAPIError, match="Network error"):
            fetch_issues("owner", "repo")
