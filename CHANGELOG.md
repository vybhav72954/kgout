# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.2.0] - 2026-03-09

### Added
- **OAuth2 user authentication** — `kgout-auth` CLI command for one-time Google Drive login. Works with free Gmail accounts. No service account needed.
- Auto-detection of credential type (service account JSON vs OAuth2 token) — same `credentials=` parameter handles both transparently
- `supportsAllDrives=True` on all Google Drive API calls — Shared Drives now work correctly
- `KGOUT_GDRIVE_FOLDER_ID` environment variable support
- `test_gdrive.py` test suite for credential detection

### Changed
- **Default destination is now `gdrive` instead of `local`**. ngrok free-tier tunnels disconnect after ~2 hours, making `local` unreliable for long training runs.
- `google-auth-oauthlib` added to `gdrive` optional dependencies (for `kgout-auth` CLI)

### Fixed
- **Service account storage quota error** (`storageQuotaExceeded`) — Google no longer allows service accounts to own files in regular Drive. OAuth2 user credentials solve this for all users. Service accounts still work with Shared Drives.
- Hidden files/folders no longer show in ngrok file browser
- File modifications correctly detected as "modified" instead of "created"
- Deleted files cleaned up from watcher registry (prevents memory leak)

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
