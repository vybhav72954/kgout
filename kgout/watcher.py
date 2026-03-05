"""Polling-based file watcher running in a background daemon thread."""

from __future__ import annotations

import fnmatch
import logging
import os
import threading
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("kgout")


class FileWatcher:
    """Watches a directory for new and modified files via periodic polling.

    Uses mtime + size fingerprinting. Runs as a daemon thread so it
    won't block notebook execution or prevent kernel shutdown.

    Parameters
    ----------
    watch_dir : str
        Root directory to watch (recursively).
    ignore_patterns : list[str]
        Glob patterns for filenames to skip.
    interval : int
        Seconds between scans.
    callback : callable
        ``callback(filepath, event)`` where event is ``"created"``
        or ``"modified"``.
    snapshot_existing : bool
        If True, take a snapshot on start and only fire events for
        changes after that. If False, treat all files as new on first scan.
    settle_time : float
        Minimum seconds since last modification before syncing a file.
        Prevents syncing files that are still being written. Default 2.0.
    """

    def __init__(
        self,
        watch_dir: str,
        ignore_patterns: List[str],
        interval: int,
        callback: Callable[[str, str], None],
        snapshot_existing: bool = True,
        settle_time: float = 2.0,
    ):
        self._watch_dir = os.path.abspath(watch_dir)
        self._ignore_patterns = ignore_patterns
        self._interval = interval
        self._callback = callback
        self._snapshot_existing = snapshot_existing
        self._settle_time = settle_time

        # filepath -> (mtime, size)
        self._registry: Dict[str, tuple] = {}
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._events_fired = 0
        self._lock = threading.Lock()

    # ── Scanning ────────────────────────────────────────────

    def _should_ignore(self, filename: str, filepath: str) -> bool:
        """Check if a file should be ignored."""
        # Hidden files
        if filename.startswith("."):
            return True
        # Path fragment checks
        path_lower = filepath.lower()
        for frag in (".ipynb_checkpoints", "__pycache__", ".git"):
            if frag in path_lower:
                return True
        # Glob pattern matching
        for pat in self._ignore_patterns:
            if fnmatch.fnmatch(filename, pat):
                return True
        return False

    def _scan(self) -> Dict[str, tuple]:
        """Walk the watch directory and return {path: (mtime, size)}."""
        import time as _time

        now = _time.time()
        snapshot: Dict[str, tuple] = {}
        for root, dirs, files in os.walk(self._watch_dir, followlinks=False):
            # Prune hidden/ignored directories in-place
            dirs[:] = [
                d for d in dirs
                if not d.startswith(".")
                and d not in ("__pycache__", ".ipynb_checkpoints", ".git")
            ]
            for fname in files:
                fpath = os.path.join(root, fname)
                if self._should_ignore(fname, fpath):
                    continue
                try:
                    st = os.stat(fpath)
                    # Skip files modified very recently — they may still be
                    # in the process of being written (partial file guard)
                    if self._settle_time > 0 and (now - st.st_mtime) < self._settle_time:
                        continue
                    snapshot[fpath] = (st.st_mtime, st.st_size)
                except OSError:
                    # File vanished between walk and stat
                    continue
        return snapshot

    def _check(self):
        """Run one scan cycle and fire callbacks for changes."""
        current = self._scan()

        # Determine changes while holding the lock, but fire callbacks outside
        # it so slow syncs (e.g. GDrive upload) don't block the next scan.
        pending = []
        with self._lock:
            for path, fingerprint in current.items():
                if path not in self._registry:
                    self._events_fired += 1
                    pending.append((path, "created"))
                elif self._registry[path] != fingerprint:
                    self._events_fired += 1
                    pending.append((path, "modified"))
            self._registry = current

        for path, event in pending:
            try:
                self._callback(path, event)
            except Exception as exc:
                logger.error("Callback error for %s: %s", path, exc)

    # ── Thread loop ─────────────────────────────────────────

    def _poll_loop(self):
        """Main polling loop — runs in daemon thread."""
        while not self._stop_event.wait(self._interval):
            try:
                self._check()
            except Exception as exc:
                logger.error("Watcher scan error: %s", exc)

    # ── Public API ──────────────────────────────────────────

    def start(self):
        """Start the watcher thread."""
        if self._thread and self._thread.is_alive():
            return

        # Snapshot existing files so we don't re-trigger them
        if self._snapshot_existing:
            self._registry = self._scan()
            logger.info(
                "📸 Snapshot: %d existing file(s) in '%s'",
                len(self._registry),
                self._watch_dir,
            )
        else:
            self._registry = {}

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._poll_loop,
            name="kgout-watcher",
            daemon=True,
        )
        self._thread.start()

    def stop(self):
        """Stop the watcher thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=self._interval + 2)
            self._thread = None

    def force_check(self):
        """Trigger an immediate scan (blocking)."""
        self._check()

    @property
    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "files_tracked": len(self._registry),
                "events_fired": self._events_fired,
            }
