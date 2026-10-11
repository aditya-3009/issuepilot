import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_ROOT = "https://api.github.com"


class GitHubAPIError(RuntimeError):
    pass


def fetch_issues(owner: str, repo: str, pages: int = 1, per_page: int = 100) -> list[dict]:
    if pages < 1:
        raise ValueError("pages must be at least 1")
    if not 1 <= per_page <= 100:
        raise ValueError("per_page must be between 1 and 100")

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    results = []
    with requests.Session() as session:
        for page in range(1, pages + 1):
            url = f"{API_ROOT}/repos/{owner}/{repo}/issues"
            try:
                response = session.get(
                    url,
                    headers=headers,
                    params={"state": "all", "per_page": per_page, "page": page, "sort": "updated"},
                    timeout=20,
                )
            except requests.RequestException as exc:
                raise GitHubAPIError(f"Network error while fetching page {page}: {exc}") from exc

            if response.status_code == 404:
                raise GitHubAPIError(f"Repository not found or not publicly accessible: {owner}/{repo}")
            if response.status_code == 403 or response.status_code == 429:
                remaining = response.headers.get("X-RateLimit-Remaining", "unknown")
                reset = response.headers.get("X-RateLimit-Reset", "unknown")
                raise GitHubAPIError(
                    f"GitHub rate limit/permission response ({response.status_code}). "
                    f"Remaining={remaining}, reset_epoch={reset}. Try later or configure GITHUB_TOKEN."
                )
            if not response.ok:
                raise GitHubAPIError(f"GitHub returned HTTP {response.status_code}: {response.text[:300]}")

            payload = response.json()
            if not isinstance(payload, list):
                raise GitHubAPIError("Unexpected response format from GitHub API.")

            # GitHub's Issues endpoint may also return pull requests.
            results.extend(item for item in payload if "pull_request" not in item)
            if len(payload) < per_page:
                break

    return results
