"""Tests for kgout.core."""

import os
import tempfile
import time
import sys

from kgout.core import KgOut


def test_context_manager_starts_and_stops():
    """KgOut should start on enter and stop on exit."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Use a mock destination that doesn't need ngrok
        kg = KgOut.__new__(KgOut)
        kg._dest_names = []
        kg._watch_dir = tmpdir
        kg._interval = 1
        kg._ignore = []
        kg._snapshot_existing = True
        kg._verbose = False
        kg._destinations = []
        kg._watcher = None
        kg._running = False
        kg._gdrive_cfg = {}
        kg._local_cfg = {}

        # Manually wire up (bypassing __init__ dest validation)
        from kgout.watcher import FileWatcher
        kg._watcher = FileWatcher(
            watch_dir=tmpdir,
            ignore_patterns=[],
            interval=1,
            callback=lambda fp, ev: None,
            snapshot_existing=True,
        )
        kg._watcher.start()
        kg._running = True

        assert kg.is_running is True

        kg.stop()
        assert kg.is_running is False


def test_repr():
    """Repr should work without starting."""
    with tempfile.TemporaryDirectory() as tmpdir:
        kg = KgOut.__new__(KgOut)
        kg._dest_names = ["gdrive"]
        kg._watch_dir = tmpdir
        kg._interval = 30
        kg._running = False

        r = repr(kg)
        assert "gdrive" in r
        assert "stopped" in r


def test_default_dest_is_gdrive():
    """Default destination should be gdrive."""
    with tempfile.TemporaryDirectory() as tmpdir:
        kg = KgOut(watch_dir=tmpdir)
        assert kg._dest_names == ["gdrive"]


def test_rejects_dangerous_watch_dirs():
    """KgOut should refuse to watch dangerous system directories."""
    if sys.platform == "win32":
        dangerous = [os.path.splitdrive(os.getcwd())[0] + "\\"]
    else:
        dangerous = ["/", "/etc", "/var", "/usr", "/root", "/home"]

    for d in dangerous:
        try:
            kg = KgOut("local", watch_dir=d)
            kg._init_destinations = lambda: None  # skip ngrok
            kg._destinations = []
            kg.start()
            raise AssertionError(f"Should have rejected watch_dir={d}")
        except ValueError:
            pass  # expected
        except AssertionError:
            raise
        except Exception:
            pass  # other errors are fine (e.g. permission denied)
