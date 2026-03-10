"""Core KgOut class — orchestrates watching and syncing."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Sequence, Union

from kgout.watcher import FileWatcher
from kgout.utils import setup_logger, DEFAULT_IGNORE_PATTERNS

logger = logging.getLogger("kgout")

# Default Kaggle working directory
_DEFAULT_WATCH_DIR = "/kaggle/working"


class KgOut:
    """Watch a directory for new/modified files and sync them to a destination.

    Parameters
    ----------
    dest : str or list[str]
        Destination(s): ``"gdrive"`` (Google Drive) and/or ``"local"`` (ngrok).
        Default is ``"gdrive"``.
    watch_dir : str
        Directory to watch. Defaults to ``/kaggle/working``.
    interval : int
        Polling interval in seconds. Default 30.
    ignore : list[str] or None
        Glob patterns to ignore. ``None`` uses sensible defaults.
    snapshot_existing : bool
        If True (default), files already present at start are NOT synced —
        only new/modified files after ``start()`` trigger sync.
        Set to False to sync everything on first scan.

    Google Drive options (when dest includes "gdrive"):
        folder_id : str
            Google Drive folder ID to upload into.
            Also checks ``KGOUT_GDRIVE_FOLDER_ID`` env var.
        credentials : str
            Path to a service account JSON key file.
            Also checks ``KGOUT_GDRIVE_CREDENTIALS`` env var.

    Local / ngrok options (when dest includes "local"):
        ngrok_token : str or None
            ngrok auth token. Also checks ``NGROK_AUTH_TOKEN`` env var.
        port : int
            Local file server port. Default 8384.

    Examples
    --------
    >>> from kgout import KgOut
    >>> kg = KgOut("gdrive", folder_id="...", credentials="...").start()
    """

    def __init__(
        self,
        dest: Union[str, Sequence[str]] = "gdrive",
        watch_dir: str = _DEFAULT_WATCH_DIR,
        interval: int = 30,
        ignore: Optional[List[str]] = None,
        snapshot_existing: bool = True,
        # gdrive options
        folder_id: Optional[str] = None,
        credentials: Optional[str] = None,
        # local/ngrok options
        ngrok_token: Optional[str] = None,
        port: int = 8384,
        # logging
        verbose: bool = True,
    ):
        self._dest_names = [dest] if isinstance(dest, str) else list(dest)
        self._watch_dir = watch_dir
        self._interval = max(5, interval)
        self._ignore = ignore if ignore is not None else list(DEFAULT_IGNORE_PATTERNS)
        self._snapshot_existing = snapshot_existing
        self._verbose = verbose

        # Destination-specific config
        self._gdrive_cfg: Dict[str, Any] = {
            "folder_id": folder_id or os.environ.get("KGOUT_GDRIVE_FOLDER_ID"),
            "credentials": credentials or os.environ.get("KGOUT_GDRIVE_CREDENTIALS"),
        }
        self._local_cfg: Dict[str, Any] = {
            "ngrok_token": ngrok_token or os.environ.get("NGROK_AUTH_TOKEN"),
            "port": port,
        }

        self._destinations: list = []
        self._watcher: Optional[FileWatcher] = None
        self._running = False

        if verbose:
            setup_logger()

    # ── Build destinations ──────────────────────────────────

    def _init_destinations(self):
        for name in self._dest_names:
            name = name.lower().strip()
            if name == "gdrive":
                self._destinations.append(self._make_gdrive())
            elif name == "local":
                self._destinations.append(self._make_local())
            else:
                raise ValueError(
                    f"Unknown destination '{name}'. Choose 'gdrive' or 'local'."
                )

    def _make_gdrive(self):
        try:
            from kgout.destinations.gdrive import GDriveDestination
        except ImportError:
            raise ImportError(
                "Google Drive support requires extra dependencies.\n"
                "Install with: pip install kgout[gdrive]"
            )
        creds_path = self._gdrive_cfg["credentials"]
        folder_id = self._gdrive_cfg["folder_id"]
        if not creds_path:
            raise ValueError(
                "Google Drive requires credentials. Provide `credentials=` path "
                "to a service account JSON, or set KGOUT_GDRIVE_CREDENTIALS env var."
            )
        if not folder_id:
            raise ValueError(
                "Google Drive requires `folder_id=` — the ID of the target folder. "
                "You can also set KGOUT_GDRIVE_FOLDER_ID env var."
            )
        return GDriveDestination(creds_path, folder_id)

    def _make_local(self):
        try:
            from kgout.destinations.local import LocalDestination
        except ImportError:
            raise ImportError(
                "Local/ngrok support requires pyngrok.\n"
                "Install with: pip install kgout[local]"
            )
        return LocalDestination(
            serve_dir=self._watch_dir,
            port=self._local_cfg["port"],
            ngrok_token=self._local_cfg["ngrok_token"],
        )

    # ── File event callback ─────────────────────────────────

    def _on_file_event(self, filepath: str, event: str):
        """Called by the watcher when a file is created or modified."""
        rel = os.path.relpath(filepath, self._watch_dir)
        logger.info("📦 [%s] %s", event.upper(), rel)

        for dest in self._destinations:
            try:
                dest.sync(filepath, rel, event)
            except Exception as exc:
                logger.error("❌ Failed to sync %s to %s: %s", rel, dest.name, exc)

    # ── Public API ──────────────────────────────────────────

    def start(self):
        """Start watching and syncing."""
        if self._running:
            logger.warning("kgout is already running.")
            return self

        # Safety: block watching root or sensitive system directories
        resolved = os.path.realpath(self._watch_dir)
        resolved_norm = resolved.replace("\\", "/").rstrip("/").lower()
        _is_windows = os.name == "nt"

        # Block filesystem roots (Linux "/" or Windows "C:", "D:", etc.)
        _is_root = (
            resolved_norm == ""
            or resolved_norm in ("/", "\\")
            or (len(resolved_norm) == 2 and resolved_norm[1] == ":")
        )

        # Block known sensitive directories (Linux only — these don't exist on Windows)
        _DANGEROUS_LINUX = (
            "/etc", "/var", "/usr", "/bin", "/sbin",
            "/root", "/home", "/proc", "/sys", "/dev",
        )
        _is_dangerous = _is_root or (not _is_windows and resolved_norm in _DANGEROUS_LINUX)

        if _is_dangerous:
            raise ValueError(
                f"Refusing to watch '{resolved}' — this would expose "
                f"sensitive system files. Use a project-specific directory."
            )

        if not os.path.isdir(self._watch_dir):
            logger.warning(
                "Watch directory '%s' does not exist. "
                "Creating it — are you running outside Kaggle?",
                self._watch_dir,
            )
            os.makedirs(self._watch_dir, exist_ok=True)

        self._init_destinations()

        # Start destinations (e.g. ngrok tunnel, gdrive auth)
        for dest in self._destinations:
            dest.start()

        # Start file watcher
        self._watcher = FileWatcher(
            watch_dir=self._watch_dir,
            ignore_patterns=self._ignore,
            interval=self._interval,
            callback=self._on_file_event,
            snapshot_existing=self._snapshot_existing,
        )
        self._watcher.start()
        self._running = True

        logger.info(
            "👀 kgout watching '%s' every %ds → %s",
            self._watch_dir,
            self._interval,
            ", ".join(self._dest_names),
        )
        return self

    def stop(self):
        """Stop watching and clean up."""
        if not self._running:
            return

        if self._watcher:
            self._watcher.stop()
            self._watcher = None

        for dest in self._destinations:
            try:
                dest.stop()
            except Exception as exc:
                logger.error("Error stopping %s: %s", dest.name, exc)

        self._destinations.clear()
        self._running = False
        logger.info("🛑 kgout stopped.")

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def stats(self) -> Dict[str, Any]:
        """Return watcher statistics."""
        if self._watcher:
            return self._watcher.stats
        return {"files_tracked": 0, "events_fired": 0}

    # ── Context manager ─────────────────────────────────────

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False  # don't suppress exceptions

    def __repr__(self):
        state = "running" if self._running else "stopped"
        return (
            f"KgOut(dest={self._dest_names}, watch='{self._watch_dir}', "
            f"interval={self._interval}s, state={state})"
        )

    def __str__(self):
        return self.__repr__()
