# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0.1] - 2026-03-07

### Fixed
- Hidden files/folders (e.g. `.virtual_documents/`) no longer show in the ngrok file browser
- File modifications now correctly detected as "modified" instead of "created"
- Deleted files are cleaned up from the watcher registry (prevents memory leak on long runs)
- Windows: dangerous directory guard now correctly blocks drive roots like `C:\`
- Windows: Linux-only paths (`/etc`, `/var`) no longer checked on Windows

## [1.0.0] - 2026-03-05

### Added
- Core file watcher with mtime + size fingerprinting
- Google Drive destination (service account auth, auto-upload)
- Local destination (ngrok tunnel + HTTP file server)
- Context manager support (`with KgOut(...) as kg:`)
- Configurable ignore patterns and polling interval
- Snapshot mode (skip pre-existing files)
- Clean notebook-friendly logging
- Full test suite
