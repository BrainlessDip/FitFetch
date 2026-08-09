"""GitHub API interactions for release checking."""

from __future__ import annotations

from ..constants import APP_NAME, NETWORK_TIMEOUT


class GitHubService:
    """Thin wrapper around the GitHub Releases API."""

    @staticmethod
    def get_latest_release(owner: str, repo: str, current_version: str) -> dict | None:
        """Fetch the latest release metadata.

        Returns a dict with keys ``tag_name``, ``body``, ``html_url``,
        ``published_at``, ``download_url`` or ``None`` on error.

        Raises:
            ConnectionError: Network unreachable.
            Timeout: Request timed out.
            ValueError: Non-200/404/403 status or invalid JSON.
        """
        import requests as _requests

        url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
        resp = _requests.get(
            url,
            headers={
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": f"{APP_NAME}/{current_version}",
            },
            timeout=NETWORK_TIMEOUT,
        )

        if resp.status_code == 404:
            raise ValueError("No releases found on GitHub.")
        if resp.status_code == 403:
            raise ValueError(
                "Update check unavailable because GitHub's rate limit has been exceeded. "
                "Please try again later or check the official releases page."
            )
        if resp.status_code != 200:
            raise ValueError(f"GitHub API returned status {resp.status_code}.")

        data = resp.json()
        tag = data.get("tag_name", "").lstrip("v")
        body = data.get("body", "No changelog available.")
        html_url = data.get("html_url", "")
        published_at = data.get("published_at", "")

        download_url = ""
        for asset in data.get("assets", []):
            name = asset.get("name", "")
            if name.lower().endswith(".exe"):
                download_url = asset.get("browser_download_url", "")
                break

        return {
            "tag": tag,
            "body": body,
            "html_url": html_url,
            "published_at": published_at,
            "download_url": download_url,
        }

    @staticmethod
    def is_newer(remote: str, local: str) -> bool:
        """Return ``True`` if *remote* version is strictly newer than *local*."""

        def parse(v: str) -> tuple[int, ...]:
            return tuple(int(x) for x in v.split(".") if x.isdigit())

        try:
            return parse(remote) > parse(local)
        except ValueError, TypeError:
            return False
