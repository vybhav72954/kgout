# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
