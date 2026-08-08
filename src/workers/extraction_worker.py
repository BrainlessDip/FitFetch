"""Background workers for link extraction."""

from __future__ import annotations

import asyncio

from PyQt6.QtCore import QThread, pyqtSignal

from ..constants import MAX_CF_THREADS, RE_FILE_ID
from ..extraction.cloudflare import CloudflareBypass
from ..logger import logger
from ..utils import extract_filename, extract_part_num


class CloudflareWorker(QThread):
    """Worker thread for V1 (Cloudflare) extraction."""

    status_update = pyqtSignal(str)
    progress_update = pyqtSignal(int)
    link_found = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    extraction_complete = pyqtSignal()

    def __init__(
        self,
        links: list[str],
        threads: int = MAX_CF_THREADS,
        delay: int = 0,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.links = links
        self.total_links = len(links)
        self.threads = threads
        self.delay = delay
        self.cf_bypass: CloudflareBypass | None = None

    def _fmt(
        self, tag: str, filename: str, part_num: str, idx: int, msg: str = ""
    ) -> str:
        base = f"{tag}: {filename}"
        if msg:
            base += f" - {msg}"
        return f"{base} - (Part: {part_num}) - [{idx}/{self.total_links}]"

    def run(self) -> None:
        try:
            self.status_update.emit("Initializing Cloudflare bypass...")
            self.cf_bypass = CloudflareBypass(threads=self.threads)
            self.status_update.emit(f"Processing {self.total_links} links...")

            for i, link in enumerate(self.links, 1):
                self.msleep(self.delay)
                filename = extract_filename(link)
                file_id_m = RE_FILE_ID.search(link)
                file_id = file_id_m.group(1) if file_id_m else None
                part_num = extract_part_num(filename)

                if not file_id:
                    self.link_found.emit(
                        self._fmt("FAILED", filename, part_num, i, "No file ID")
                    )
                    self.progress_update.emit(i)
                    continue

                _, page_source, status_code, headers = self.cf_bypass.fetch(
                    f"https://fuckingfast.co/f/{file_id}/go", method="POST"
                )
                self.status_update.emit(
                    self._fmt(
                        "Processing", filename, part_num, i, f"Status: {status_code}"
                    )
                )

                if page_source and status_code == 429:
                    retry_after = headers.get("Retry-After") if headers else None
                    try:
                        retry_seconds = int(retry_after) if retry_after else 60
                    except (ValueError, TypeError):
                        retry_seconds = 60
                    self.link_found.emit(
                        f"RATE LIMITED: {filename} - Try again in {retry_seconds} seconds - (Part: {part_num}) - [{i}/{self.total_links}]"
                    )
                    self.status_update.emit(
                        self._fmt("Rate Limited", filename, part_num, i)
                    )

                elif page_source and status_code == 403:
                    lower_src = page_source.lower()
                    if (
                        "cf-challenge" in lower_src
                        or "cloudflare" in lower_src
                        or "just a moment" in lower_src
                    ):
                        self.link_found.emit(
                            self._fmt(
                                "CLOUDFLARE", filename, part_num, i, "Protected, use V2"
                            )
                        )
                        self.status_update.emit(
                            self._fmt("Cloudflare detected", filename, part_num, i)
                        )

                elif page_source and status_code == 200:
                    extracted_url = headers.get("Hx-Redirect") if headers else None
                    if extracted_url:
                        self.link_found.emit(extracted_url + f"#{filename}")
                        self.status_update.emit(
                            self._fmt("Extracted", filename, part_num, i)
                        )
                    else:
                        self.link_found.emit(
                            self._fmt(
                                "FAILED", filename, part_num, i, "No direct link found"
                            )
                        )
                        self.status_update.emit(
                            self._fmt("Failed", filename, part_num, i)
                        )
                else:
                    self.link_found.emit(
                        self._fmt(
                            "FAILED", filename, part_num, i, f"Status {status_code}"
                        )
                    )
                    self.status_update.emit(self._fmt("Failed", filename, part_num, i))

                self.progress_update.emit(i)

            self.status_update.emit("Extraction complete (V1)")
            self.extraction_complete.emit()

        except Exception as exc:
            logger.exception("CloudflareWorker error")
            self.error_occurred.emit(f"Cloudflare error: {exc}")


class ZendriverWorker(QThread):
    """Worker thread for V2 (Browser) extraction."""

    status_update = pyqtSignal(str)
    progress_update = pyqtSignal(int)
    link_found = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    extraction_complete = pyqtSignal()

    def __init__(
        self,
        links: list[str],
        delay: int = 3,
        browser_executable_path: str | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.links = links
        self.total_links = len(links)
        self.delay = delay
        self.browser_executable_path = browser_executable_path
        self._shutdown_requested = False
        self._client = None

    def run(self) -> None:
        try:
            asyncio.run(self._async_run())
        except Exception as exc:
            if not self._shutdown_requested:
                logger.exception("ZendriverWorker error")
                self.error_occurred.emit(f"Zendriver error: {exc}")

    async def _async_run(self) -> None:
        from ..browser.zendriver_client import ZendriverClient, resolve_direct_url

        client = ZendriverClient()
        self._client = client

        try:
            self.status_update.emit("Initializing browser (V2)...")
            await client.start(browser_executable_path=self.browser_executable_path)

            self.status_update.emit(f"Processing {self.total_links} links...")
            tab = await client.navigate("https://fuckingfast.co")

            if not await client.handle_cloudflare(tab):
                if self._shutdown_requested:
                    return
                self.error_occurred.emit(
                    "Cloudflare verification failed.\n"
                    "Please try again or use a different browser."
                )
                return

            self.status_update.emit("Cloudflare cleared. Starting extraction...")
            for i, link in enumerate(self.links, 1):
                if self._shutdown_requested:
                    break

                filename = extract_filename(link)
                part_num = extract_part_num(filename)
                self.status_update.emit(
                    f"[{i}/{self.total_links}] Processing {filename} - (Part: {part_num})"
                )

                try:
                    self.status_update.emit(
                        f"Extracting from {filename}... - (Part: {part_num}) - [{i}/{self.total_links}]"
                    )
                    download_url, cf_clearance, err = await resolve_direct_url(tab, link)
                    if not download_url:
                        error_msg = err or "No HX-Redirect received"
                        self.link_found.emit(
                            f"FAILED: {filename} - {error_msg} - (Part: {part_num}) - [{i}/{self.total_links}]"
                        )
                    else:
                        self.link_found.emit(download_url + f"#{filename}")
                        self.status_update.emit(
                            f"Extracted: {filename} - (Part: {part_num}) - [{i}/{self.total_links}]"
                        )
                except Exception as exc:
                    logger.debug(
                        "Zendriver extraction failed for %s: %s", filename, exc
                    )
                    self.link_found.emit(
                        f"FAILED: {filename} - {exc} - (Part: {part_num}) - [{i}/{self.total_links}]"
                    )

                self.progress_update.emit(i)

                if not self._shutdown_requested and i < self.total_links:
                    await asyncio.sleep(self.delay)

            self.status_update.emit("Extraction complete (V2)")
            self.extraction_complete.emit()

        except Exception as exc:
            if not self._shutdown_requested:
                logger.exception("ZendriverWorker async error")
                self.error_occurred.emit(f"Zendriver error: {exc}")
        finally:
            await client.stop()
