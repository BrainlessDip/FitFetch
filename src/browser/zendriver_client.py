"""Zendriver wrapper — isolates all zendriver-specific code."""

from __future__ import annotations

import asyncio

from ..constants import (
    ZENDRIVER_BROWSER_ARGS,
    ZENDRIVER_CF_VERIFY_CLICK_DELAY,
    ZENDRIVER_CF_VERIFY_TIMEOUT,
)
from ..logger import logger


class ZendriverClient:
    """High-level wrapper around the *zendriver* library."""

    def __init__(self) -> None:
        self._browser = None

    # -- lifecycle -----------------------------------------------------------

    async def start(self, browser_executable_path: str | None = None) -> None:
        """Launch a new browser instance."""
        import zendriver as zd

        kwargs: dict = {
            "headless": False,
            "browser_args": list(ZENDRIVER_BROWSER_ARGS),
        }
        if browser_executable_path:
            kwargs["browser_executable_path"] = browser_executable_path
        self._browser = await zd.start(**kwargs)

    async def stop(self) -> None:
        """Stop the browser, ignoring errors."""
        if self._browser is None:
            return
        try:
            await self._browser.stop()
        except Exception:
            logger.debug("Error stopping browser", exc_info=True)
            try:
                await self._browser.stop()
            except Exception:
                pass

    # -- navigation ----------------------------------------------------------

    async def navigate(self, url: str):
        """Navigate to *url* and return the tab object."""
        tab = await self._browser.get(url)
        await tab.wait_for_ready_state("complete")
        return tab

    # -- Cloudflare ----------------------------------------------------------

    async def handle_cloudflare(self, tab) -> bool:
        """Detect and solve a Cloudflare interactive challenge.

        Returns ``True`` if the challenge was absent or solved successfully.
        """
        from zendriver.core.cloudflare import (
            cf_is_interactive_challenge_present,
            verify_cf,
        )

        try:
            is_present = await cf_is_interactive_challenge_present(tab, timeout=2)
            if not is_present:
                return True
            await verify_cf(
                tab,
                click_delay=ZENDRIVER_CF_VERIFY_CLICK_DELAY,
                timeout=ZENDRIVER_CF_VERIFY_TIMEOUT,
            )
            return True
        except TimeoutError:
            return False
        except Exception as exc:
            logger.debug("Cloudflare handling error: %s", exc)
            return False

    # -- extraction ----------------------------------------------------------

    async def extract_link(self, tab, file_id: str) -> str | None:
        """Extract a direct download link via JS fetch on the page."""
        headers = await tab.evaluate(
            f'(async()=>Object.fromEntries((await fetch("/f/{file_id}/go",{{method:"POST"}})).headers.entries()))()',
            await_promise=True,
        )
        if headers and "hx-redirect" in headers:
            return headers["hx-redirect"]
        return None
