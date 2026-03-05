"""Tests for kgout.watcher."""

import os
import tempfile
import time

from kgout.watcher import FileWatcher


def test_detects_new_file():
    """Watcher should fire 'created' when a new file appears."""
    events = []

    with tempfile.TemporaryDirectory() as tmpdir:
        watcher = FileWatcher(
            watch_dir=tmpdir,
            ignore_patterns=["*.tmp"],
            interval=1,
            callback=lambda fp, ev: events.append((os.path.basename(fp), ev)),
            snapshot_existing=True,
            settle_time=0,
        )
        watcher.start()

        # Create a file after watcher starts
        time.sleep(0.5)
        with open(os.path.join(tmpdir, "results.csv"), "w") as f:
            f.write("col1,col2\n1,2\n")

        # Wait for at least one poll cycle
        time.sleep(2)
        watcher.stop()

    assert len(events) >= 1
    assert events[0] == ("results.csv", "created")


def test_detects_modified_file():
    """Watcher should fire 'modified' when a file changes."""
    events = []

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create file before starting watcher
        fpath = os.path.join(tmpdir, "model.pt")
        with open(fpath, "w") as f:
            f.write("v1")

        watcher = FileWatcher(
            watch_dir=tmpdir,
            ignore_patterns=[],
            interval=1,
            callback=lambda fp, ev: events.append((os.path.basename(fp), ev)),
            snapshot_existing=True,
            settle_time=0,
        )
        watcher.start()

        # Modify the file
        time.sleep(0.5)
        with open(fpath, "w") as f:
            f.write("v2 with more data")

        time.sleep(2)
        watcher.stop()

    assert any(ev == "modified" for _, ev in events)


def test_ignores_patterns():
    """Files matching ignore patterns should not trigger events."""
    events = []

    with tempfile.TemporaryDirectory() as tmpdir:
        watcher = FileWatcher(
            watch_dir=tmpdir,
            ignore_patterns=["*.tmp", "*.log"],
            interval=1,
            callback=lambda fp, ev: events.append(os.path.basename(fp)),
            snapshot_existing=True,
            settle_time=0,
        )
        watcher.start()

        time.sleep(0.5)
        # These should be ignored
        with open(os.path.join(tmpdir, "debug.log"), "w") as f:
            f.write("log")
        with open(os.path.join(tmpdir, "temp.tmp"), "w") as f:
            f.write("tmp")
        # This should be detected
        with open(os.path.join(tmpdir, "output.csv"), "w") as f:
            f.write("data")

        time.sleep(2)
        watcher.stop()

    assert "output.csv" in events
    assert "debug.log" not in events
    assert "temp.tmp" not in events


def test_ignores_hidden_files():
    """Hidden files (starting with .) should be ignored."""
    events = []

    with tempfile.TemporaryDirectory() as tmpdir:
        watcher = FileWatcher(
            watch_dir=tmpdir,
            ignore_patterns=[],
            interval=1,
            callback=lambda fp, ev: events.append(os.path.basename(fp)),
            snapshot_existing=True,
            settle_time=0,
        )
        watcher.start()

        time.sleep(0.5)
        with open(os.path.join(tmpdir, ".hidden"), "w") as f:
            f.write("secret")
        with open(os.path.join(tmpdir, "visible.txt"), "w") as f:
            f.write("hello")

        time.sleep(2)
        watcher.stop()

    assert "visible.txt" in events
    assert ".hidden" not in events


def test_snapshot_existing_skips_old_files():
    """With snapshot_existing=True, pre-existing files should not fire events."""
    events = []

    with tempfile.TemporaryDirectory() as tmpdir:
        # Pre-existing file
        with open(os.path.join(tmpdir, "old.csv"), "w") as f:
            f.write("old data")

        watcher = FileWatcher(
            watch_dir=tmpdir,
            ignore_patterns=[],
            interval=1,
            callback=lambda fp, ev: events.append((os.path.basename(fp), ev)),
            snapshot_existing=True,
            settle_time=0,
        )
        watcher.start()
        time.sleep(2)
        watcher.stop()

    # old.csv should NOT appear — it existed before the watcher started
    assert not any(name == "old.csv" and ev == "created" for name, ev in events)


def test_no_snapshot_fires_for_existing():
    """With snapshot_existing=False, existing files should fire as 'created'."""
    events = []

    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "old.csv"), "w") as f:
            f.write("old data")

        watcher = FileWatcher(
            watch_dir=tmpdir,
            ignore_patterns=[],
            interval=1,
            callback=lambda fp, ev: events.append((os.path.basename(fp), ev)),
            snapshot_existing=False,
            settle_time=0,
        )
        watcher.start()
        time.sleep(2)
        watcher.stop()

    assert ("old.csv", "created") in events


def test_stats():
    """Stats should report tracked files and events."""
    events = []

    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "existing.txt"), "w") as f:
            f.write("data")

        watcher = FileWatcher(
            watch_dir=tmpdir,
            ignore_patterns=[],
            interval=1,
            callback=lambda fp, ev: events.append(ev),
            snapshot_existing=True,
            settle_time=0,
        )
        watcher.start()

        stats = watcher.stats
        assert stats["files_tracked"] == 1

        time.sleep(0.5)
        with open(os.path.join(tmpdir, "new.txt"), "w") as f:
            f.write("new")

        time.sleep(2)
        watcher.stop()

        stats = watcher.stats
        assert stats["events_fired"] >= 1


def test_settle_time_delays_detection():
    """Files modified very recently should not trigger events until settled."""
    events = []

    with tempfile.TemporaryDirectory() as tmpdir:
        watcher = FileWatcher(
            watch_dir=tmpdir,
            ignore_patterns=[],
            interval=1,
            callback=lambda fp, ev: events.append((os.path.basename(fp), ev)),
            snapshot_existing=True,
            settle_time=3.0,  # high settle time
        )
        watcher.start()

        time.sleep(0.5)
        with open(os.path.join(tmpdir, "fresh.csv"), "w") as f:
            f.write("data")

        # After 1.5s total — file is only ~1s old, below 3s settle_time
        time.sleep(1)
        watcher.force_check()
        events_at_1s = list(events)

        # After 4.5s total — file is ~4s old, above 3s settle_time
        time.sleep(3)
        watcher.force_check()
        events_at_4s = list(events)

        watcher.stop()

    assert len(events_at_1s) == 0, "File should NOT be detected before settle_time"
    assert any(name == "fresh.csv" for name, _ in events_at_4s), "File SHOULD be detected after settle_time"
