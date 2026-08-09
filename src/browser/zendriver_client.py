"""Zendriver wrapper — isolates all zendriver-specific code."""

from __future__ import annotations

from ..constants import (
    RE_FILE_ID,
    ZENDRIVER_BROWSER_ARGS,
    ZENDRIVER_CF_VERIFY_CLICK_DELAY,
    ZENDRIVER_CF_VERIFY_TIMEOUT,
)
from ..logger import logger


class ZendriverClient:
    """High-level wrapper around the *zendriver* library."""

    def __init__(
        self,
        window_position: tuple[int, int] | None = None,
        user_data_dir: str | None = None,
    ) -> None:
        self._browser = None
        self._window_position = window_position
        self._user_data_dir = user_data_dir

    # -- lifecycle -----------------------------------------------------------

    async def start(self, browser_executable_path: str | None = None) -> None:
        """Launch a new browser instance."""
        import zendriver as zd

        kwargs: dict = {
            "headless": False,
            "browser_args": list(ZENDRIVER_BROWSER_ARGS),
        }
        if self._user_data_dir:
            kwargs["browser_args"].append(f"--user-data-dir={self._user_data_dir}")
        if self._window_position is not None:
            kwargs["browser_args"].append(
                f"--window-position="
                f"{self._window_position[0]},{self._window_position[1]}"
            )
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
        return await _solve_cloudflare(tab)


async def _solve_cloudflare(tab) -> bool:
    """Wait for and solve a Cloudflare/Turnstile challenge, if present."""
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


async def get_cf_clearance(tab, retries: int = 10, delay: float = 0.5) -> str | None:
    """Read the ``cf_clearance`` cookie via CDP.

    The cookie is HttpOnly, so it is not exposed through
    ``document.cookie``; it must be read from the browser directly.

    Polls for a short while because the cookie is set by Cloudflare
    right as the challenge is solved, so it may not exist instantly.
    """
    from zendriver.cdp import network as cdp_network

    import asyncio

    for attempt in range(retries):
        try:
            cookies = await tab.send(cdp_network.get_all_cookies())
        except Exception as exc:
            logger.debug("Failed to read cf_clearance cookie: %s", exc)
            return None
        for cookie in cookies:
            if cookie.name == "cf_clearance":
                return cookie.value
        if attempt < retries - 1:
            await asyncio.sleep(delay)
    return None


async def clear_host_data(tab, url: str) -> None:
    """Clear cookies and storage for *url*'s host via CDP.

    Ensures each request starts with a fresh cookie jar so a new
    ``cf_clearance`` is issued by Cloudflare on the next solve.
    """
    from urllib.parse import urlsplit

    from zendriver.cdp import network as cdp_network
    from zendriver.cdp import storage as cdp_storage

    origin = f"{urlsplit(url).scheme}://{urlsplit(url).netloc}"
    try:
        await tab.send(cdp_network.clear_browser_cookies())
    except Exception as exc:
        logger.debug("Failed to clear browser cookies: %s", exc)
    try:
        await tab.send(cdp_network.clear_browser_cache())
    except Exception as exc:
        logger.debug("Failed to clear browser cache: %s", exc)
    try:
        storage_types = ",".join(
            [
                "cookies",
                "local_storage",
                "session_storage",
                "indexeddb",
                "cache_storage",
            ]
        )
        await tab.send(cdp_storage.clear_data_for_origin(origin, storage_types))
    except Exception as exc:
        logger.debug("Failed to clear host data for %s: %s", origin, exc)
    logger.info("[CLEAR] host data cleared for %s", origin)


async def resolve_direct_url(tab, link: str) -> tuple[str | None, str | None]:
    """Resolve the direct download URL for a FuckingFast link.

    Opens *link* in the given *tab*, waits for Cloudflare/Turnstile to be
    ready, grabs the Turnstile token, POSTs to ``/f/{file_id}/go`` exactly like
    the site's download button, and reads the ``HX-Redirect`` response header.

    Returns ``(direct_url, None)`` on success or
    ``(None, None, error)`` on failure.
    """
    file_id_m = RE_FILE_ID.search(link)
    if not file_id_m:
        return None, None, f"No file ID found in {link}"
    file_id = file_id_m.group(1)

    page_url = link.split("#")[0]
    await clear_host_data(tab, page_url)
    try:
        await tab.get(page_url)
        await tab.wait_for_ready_state("complete")
    except Exception as exc:
        logger.debug("Navigation failed for %s: %s", page_url, exc)
        return None, None, f"Navigation failed: {exc}"

    if not await _solve_cloudflare(tab):
        return None, None, "Turnstile/Cloudflare verification failed"

    post_path = f"/f/{file_id}/go"
    logger.info("[POST] %s", post_path)

    token_expr = "window.turnstileToken||(el&&el.value)"

    script = (
        "(async()=>{"
        "try{"
        "const el=document.querySelector('[name=\"cf-turnstile-response\"]');"
        f"const t={token_expr};"
        "if(!t){return {error:'no_turnstile_token'}}"
        "const r=await fetch(" + repr(post_path) + ",{"
        "method:'POST',"
        "headers:{"
        "'content-type':'application/x-www-form-urlencoded',"
        "'hx-request':'true',"
        "'hx-current-url':location.href,"
        "'referer':location.href"
        "},"
        "body:new URLSearchParams({'cf-turnstile-response':t})"
        "});"
        "return "
        "{status:r.status,"
        "hxRedirect:(r.headers.get('HX-Redirect')||r.headers.get('hx-redirect'))||null"
        "};"
        "}catch(e){return {error:'fetch:'+String(e&&e.message||e)}}"
        "})()"
    )

    try:
        result = await tab.evaluate(script, await_promise=True)
    except Exception as exc:
        logger.debug("POST fetch failed for %s: %s", post_path, exc)
        return None, None, f"POST request failed: {exc}"

    if not isinstance(result, dict):
        logger.debug("Unexpected POST response: %r", result)
        return None, None, f"Unexpected response body ({type(result).__name__})"

    if "error" in result:
        error = str(result["error"])
        if error == "no_turnstile_token":
            logger.debug("Turnstile token unavailable on %s", page_url)
            return None, None, "Turnstile token unavailable"
        return None, None, f"POST request failed: {error}"

    status = result.get("status")
    if status is not None:
        try:
            status = int(status)
        except TypeError, ValueError:
            status = None
    logger.info("[STATUS] %s", status)
    if status is None or not (200 <= status < 300):
        return None, None, f"POST failed with non-2xx status {status}"

    direct_url = result.get("hxRedirect") or ""
    if not direct_url:
        return None, None, "HX-Redirect header missing from response"

    logger.info("[HX-REDIRECT] %s", direct_url)
    return direct_url, None
