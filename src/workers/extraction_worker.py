"""Background workers for link extraction."""

from __future__ import annotations

import asyncio
import queue
import threading

from PyQt6.QtCore import QThread, pyqtSignal

from ..constants import RE_FILE_ID
from ..extraction.cloudflare import CloudflareBypass
from ..logger import logger
from ..utils import (
    extract_filename,
    extract_part_num,
    remove_worker_profile_dir,
)


class CloudflareWorker(QThread):
    """Worker thread for V1 (Cloudflare) extraction.

    Spawns ``workers`` daemon threads that pull ``(index, link)`` tuples from
    one shared queue, so requests overlap instead of running one at a time.
    A single lock guards the completed-counter increment *and* the signal
    emission together; Qt delivers queued signal events FIFO to the receiver,
    so serialising the emit under that lock is what keeps the aggregate
    progress count monotonic across concurrent workers.

    Workers are numbered from 1. ``progress_update`` carries the aggregate
    number of finished links; ``worker_progress`` carries a single worker's
    own count, which has no fixed denominator because work is pulled
    dynamically rather than statically batched.
    """

    status_update = pyqtSignal(str)
    progress_update = pyqtSignal(int)
    worker_progress = pyqtSignal(int, int)
    link_found = pyqtSignal(str)
    link_failed = pyqtSignal(str, str)
    error_occurred = pyqtSignal(str)
    extraction_complete = pyqtSignal()

    def __init__(
        self,
        links: list[str],
        workers: int = 1,
        delay: int = 0,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.links = links
        self.total_links = len(links)
        self.workers = max(1, int(workers))
        self.delay = delay
        self.cf_bypass: CloudflareBypass | None = None
        self._shutdown_requested = False
        self._progress_lock = threading.Lock()
        self._completed = 0
        self._worker_counts: dict[int, int] = {}
        self._work_queue: queue.Queue | None = None

    def _fmt(
        self, tag: str, filename: str, part_num: str, idx: int, msg: str = ""
    ) -> str:
        base = f"{tag}: {filename}"
        if msg:
            base += f" - {msg}"
        return f"{base} - (Part: {part_num}) - [{idx}/{self.total_links}]"

    def request_shutdown(self) -> None:
        """Ask the workers to stop and wake any that are parked.

        Safe to call from the GUI thread while :meth:`run` executes on the
        QThread: ``queue.Queue.put`` is thread-safe.
        """
        self._shutdown_requested = True
        pending = self._work_queue
        if pending is not None:
            for _ in range(self.workers):
                pending.put(None)

    def run(self) -> None:
        try:
            self.status_update.emit("Initializing Cloudflare bypass...")
            self.cf_bypass = CloudflareBypass(threads=self.workers)
            self.status_update.emit(
                f"Processing {self.total_links} links "
                f"across {self.workers} parallel worker(s)..."
            )

            work: queue.Queue = queue.Queue()
            self._work_queue = work
            for index, link in enumerate(self.links, 1):
                work.put((index, link))
            # One exit sentinel per worker, queued behind all real work so
            # every link is consumed before any worker stops.
            for _ in range(self.workers):
                work.put(None)

            self._worker_counts = {i: 0 for i in range(1, self.workers + 1)}
            threads = [
                threading.Thread(
                    target=self._worker_loop,
                    args=(wid, work),
                    name=f"cf-worker-{wid}",
                    daemon=True,
                )
                for wid in range(1, self.workers + 1)
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

            self.status_update.emit("Extraction complete (V1)")
            self.extraction_complete.emit()

        except Exception as exc:
            logger.exception("CloudflareWorker error")
            self.error_occurred.emit(f"Cloudflare error: {exc}")

    def _worker_loop(self, wid: int, work: queue.Queue) -> None:
        """Pull links until the queue drains or shutdown is requested."""
        while not self._shutdown_requested:
            try:
                item = work.get(timeout=0.25)
            except queue.Empty:
                # Timeout lets the loop re-check the shutdown flag rather
                # than blocking forever on an exhausted queue.
                continue
            if item is None:
                break

            index, link = item
            if self.delay:
                self.msleep(self.delay)
            filename, part_num = link, "0"

            try:
                filename = extract_filename(link)
                part_num = extract_part_num(filename)
                self._process_link(link, index, filename, part_num)
            except Exception as exc:
                # One bad link must not abort the run: record it and carry on.
                logger.exception("V1 worker %s failed on %s", wid, filename)
                self.link_found.emit(
                    self._fmt("FAILED", filename, part_num, index, str(exc))
                )
                self.link_failed.emit(link, str(exc))
            finally:
                self._record_completion(wid)

    def _record_completion(self, wid: int) -> None:
        """Advance the aggregate and per-worker counters under one lock.

        The emit must stay inside the ``with`` block. Qt posts queued signal
        events FIFO to the receiver's queue, so holding the mutex across the
        emit is what guarantees the bar never steps backwards.
        """
        with self._progress_lock:
            self._completed += 1
            self._worker_counts[wid] = self._worker_counts.get(wid, 0) + 1
            self.progress_update.emit(self._completed)
            self.worker_progress.emit(wid, self._worker_counts[wid])

    def _process_link(
        self, link: str, index: int, filename: str, part_num: str
    ) -> None:
        """Classify one link and emit the matching signals.

        *index* is the link's original position in the input list, so log
        lines stay stable no matter which worker handled it. The status
        classification below is unchanged from the former sequential loop.
        """
        file_id_m = RE_FILE_ID.search(link)
        file_id = file_id_m.group(1) if file_id_m else None

        if not file_id:
            self.link_found.emit(
                self._fmt("FAILED", filename, part_num, index, "No file ID")
            )
            self.link_failed.emit(link, "No file ID")
            return

        _, page_source, status_code, headers = self.cf_bypass.fetch(
            f"https://fuckingfast.co/f/{file_id}/go", method="POST"
        )
        self.status_update.emit(
            self._fmt("Processing", filename, part_num, index, f"Status: {status_code}")
        )

        if page_source and status_code == 429:
            retry_after = headers.get("Retry-After") if headers else None
            try:
                retry_seconds = int(retry_after) if retry_after else 60
            except (ValueError, TypeError):
                retry_seconds = 60
            self.link_found.emit(
                f"RATE LIMITED: {filename} - Try again in {retry_seconds} seconds - (Part: {part_num}) - [{index}/{self.total_links}]"
            )
            self.link_failed.emit(
                link, f"Rate limited - retry in {retry_seconds} seconds"
            )
            self.status_update.emit(
                self._fmt("Rate Limited", filename, part_num, index)
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
                        "CLOUDFLARE", filename, part_num, index, "Protected, use V2"
                    )
                )
                self.link_failed.emit(link, "Cloudflare protected - use V2")
                self.status_update.emit(
                    self._fmt("Cloudflare detected", filename, part_num, index)
                )

        elif page_source and status_code == 200:
            extracted_url = headers.get("Hx-Redirect") if headers else None
            if extracted_url:
                self.link_found.emit(extracted_url + f"#{filename}")
                self.status_update.emit(
                    self._fmt("Extracted", filename, part_num, index)
                )
            else:
                self.link_found.emit(
                    self._fmt(
                        "FAILED", filename, part_num, index, "No direct link found"
                    )
                )
                self.link_failed.emit(link, "No direct link found")
                self.status_update.emit(
                    self._fmt("Failed", filename, part_num, index)
                )
        else:
            self.link_found.emit(
                self._fmt(
                    "FAILED", filename, part_num, index, f"Status {status_code}"
                )
            )
            self.link_failed.emit(link, f"Status {status_code}")
            self.status_update.emit(
                self._fmt("Failed", filename, part_num, index)
            )


class ZendriverWorker(QThread):
    """Worker thread for V2 (Browser) extraction."""

    status_update = pyqtSignal(str)
    progress_update = pyqtSignal(int)
    link_found = pyqtSignal(str, str)
    link_failed = pyqtSignal(str, str)
    error_occurred = pyqtSignal(str)
    extraction_complete = pyqtSignal()

    def __init__(
        self,
        links: list[str],
        delay: int = 3000,
        browser_executable_path: str | None = None,
        window_position: tuple[int, int] | None = None,
        profile_index: int = 1,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.links = links
        self.total_links = len(links)
        self.delay = delay
        self.browser_executable_path = browser_executable_path
        self.window_position = window_position
        self.profile_index = profile_index
        self._profile_dir = None
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
        from ..utils import get_worker_profile_dir

        self._profile_dir = str(get_worker_profile_dir(self.profile_index))
        client = ZendriverClient(
            window_position=self.window_position,
            user_data_dir=self._profile_dir,
        )
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
                    download_url, err = await resolve_direct_url(tab, link)
                    if not download_url:
                        error_msg = err or "No HX-Redirect received"
                        self.link_failed.emit(link, error_msg)
                    else:
                        self.link_found.emit(link, download_url + f"#{filename}")
                        self.status_update.emit(
                            f"Extracted: {filename} - (Part: {part_num}) - [{i}/{self.total_links}]"
                        )
                except Exception as exc:
                    logger.debug(
                        "Zendriver extraction failed for %s: %s", filename, exc
                    )
                    self.link_failed.emit(link, str(exc))

                self.progress_update.emit(i)

                if not self._shutdown_requested and i < self.total_links:
                    await asyncio.sleep(self.delay / 1000)

            self.status_update.emit("Extraction complete (V2)")
            self.extraction_complete.emit()

        except Exception as exc:
            if not self._shutdown_requested:
                logger.exception("ZendriverWorker async error")
                self.error_occurred.emit(f"Zendriver error: {exc}")
        finally:
            await client.stop()
            if self._profile_dir:
                remove_worker_profile_dir(self.profile_index)
