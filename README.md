# kgout

**Auto-sync Kaggle notebook outputs to Google Drive or your local machine.**

[![PyPI version](https://badge.fury.io/py/kgout.svg)](https://pypi.org/project/kgout/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

When running long ML experiments on Kaggle, kernels can time out or sessions expire — and your output files disappear. **kgout** watches `/kaggle/working/` in the background and automatically syncs new or modified files to Google Drive or exposes them via an ngrok tunnel for instant local download.

Drop it into any notebook as a single cell.

## Install

```bash
# Google Drive support (recommended for long runs)
pip install kgout[gdrive]

# Local/ngrok tunnel support (for quick experiments < 2 hours)
pip install kgout[local]

# Everything
pip install kgout[all]
```

## Quick Start

### Google Drive Auto-Upload (Recommended)

Every new CSV, checkpoint, or plot auto-uploads to a Drive folder the moment it's saved. Works for runs of any length. Survives session disconnects.

```python
from kgout import KgOut

kg = KgOut(
    folder_id="1ABCxyz_your_drive_folder_id",
    credentials="/kaggle/input/my-creds/service_account.json",
).start()

# ... your training code ...
# New files auto-upload to Google Drive as they appear.
# No kg.stop() needed — uploads continue until the kernel ends.
```

See [Setting Up Google Drive](#setting-up-google-drive) below for the one-time setup.

### Local Download via ngrok

Exposes your `/kaggle/working/` directory as a browsable URL. Good for quick experiments under 2 hours.

```python
import os
os.environ["NGROK_AUTH_TOKEN"] = "your_token_here"  # free at ngrok.com

from kgout import KgOut

kg = KgOut("local").start()
# Open the printed URL in your browser to download files instantly.
# ⚠️  ngrok free tier disconnects after ~2 hours.
```

### Both at Once (Recommended for Long Runs with Live Access)

Google Drive for persistence, ngrok for instant browsing while it lasts:

```python
kg = KgOut(
    dest=["gdrive", "local"],
    folder_id="1ABCxyz",
    credentials="/kaggle/input/my-creds/service_account.json",
).start()
# Files upload to Drive AND are browsable via ngrok.
# When ngrok disconnects after ~2h, Drive uploads continue uninterrupted.
```

### Context manager vs manual start

```python
# ✅ RECOMMENDED for Kaggle — stays alive after training ends
kg = KgOut(...).start()
train_model()
# ← still running, download/upload continues
# kg.stop()  # only call when you're truly done

# ⚠️  Context manager — STOPS when the block ends
with KgOut(...) as kg:
    train_model()
# ← dead here, can't download/upload!
```

**For Kaggle notebooks, always use `.start()` instead of `with KgOut(...)`.** The context manager kills everything the moment your code finishes. With `.start()`, syncing continues for the entire kernel session (up to 12 hours).

## Setting Up Google Drive

One-time setup (takes 5 minutes):

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project (or use existing) and enable the **Google Drive API**
3. Go to **IAM & Admin > Service Accounts** > Create a service account
4. Create a key (JSON type) > download it
5. Upload the JSON to Kaggle as a **private dataset** (e.g., `my-creds`)
6. In Google Drive, create a folder for outputs > right-click > **Share** > paste the service account email (the `client_email` field in the JSON) > give it **Editor** access
7. Copy the folder ID from the Drive URL:
   ```
   https://drive.google.com/drive/folders/1aBcDeFgHiJkLmNoPqRsTuVwXyZ
                                           └──── this is folder_id ────┘
   ```
8. In your notebook:
   ```python
   kg = KgOut(
       folder_id="1aBcDeFgHiJkLmNoPqRsTuVwXyZ",
       credentials="/kaggle/input/my-creds/service_account.json",
   ).start()
   ```

That's it. Every file saved to `/kaggle/working/` from this point forward auto-uploads to your Drive folder.

## Setting Up ngrok (for local destination)

1. Create a free account at [ngrok.com](https://ngrok.com)
2. Copy your auth token from [the dashboard](https://dashboard.ngrok.com/get-started/your-authtoken)
3. In your Kaggle notebook:
   ```python
   import os
   os.environ["NGROK_AUTH_TOKEN"] = "your_token"
   ```
   Or pass it directly: `KgOut("local", ngrok_token="your_token")`

**Tip:** On Kaggle, store the token as a [Kaggle Secret](https://www.kaggle.com/discussions/product-feedback/114053):
```python
from kaggle_secrets import UserSecretsClient
os.environ["NGROK_AUTH_TOKEN"] = UserSecretsClient().get_secret("NGROK_AUTH_TOKEN")
```

## Configuration

| Parameter | Default | Description |
|---|---|---|
| `dest` | `"gdrive"` | `"gdrive"`, `"local"`, or `["gdrive", "local"]` |
| `watch_dir` | `/kaggle/working` | Directory to watch (recursive) |
| `interval` | `30` | Seconds between scans (min: 5) |
| `ignore` | see below | Glob patterns for files to skip |
| `snapshot_existing` | `True` | If True, skip files that exist before `start()` |
| `folder_id` | — | Google Drive folder ID (required for gdrive) |
| `credentials` | — | Service account JSON path (required for gdrive) |
| `ngrok_token` | — | ngrok auth token (or set `NGROK_AUTH_TOKEN` env var) |
| `port` | `8384` | Local file server port |
| `verbose` | `True` | Enable logging output |

### Environment Variables

All credentials can come from environment variables instead of parameters:

| Variable | Used by | Description |
|---|---|---|
| `KGOUT_GDRIVE_FOLDER_ID` | `gdrive` destination | Google Drive folder ID |
| `KGOUT_GDRIVE_CREDENTIALS` | `gdrive` destination | Path to service account JSON |
| `NGROK_AUTH_TOKEN` | `local` destination | ngrok authentication token |

## Default Ignore Patterns

These files are never synced:

- `*.ipynb`, `*.pyc`, `*.tmp`, `*.lock`, `*.log`, `*.swp`, `*.swo`
- `.DS_Store`, `Thumbs.db`
- Hidden files (starting with `.`)
- Directories: `.ipynb_checkpoints`, `__pycache__`, `.git`

Override with `ignore=["*.csv"]` or pass `ignore=[]` to sync everything.

## How It Works

1. **Snapshot**: On `start()`, kgout fingerprints all existing files (mtime + size) so they don't trigger syncs
2. **Poll**: A daemon thread scans the watch directory every N seconds
3. **Settle check**: Files modified in the last 2 seconds are skipped (still being written)
4. **Compare**: Each file's fingerprint is compared against the snapshot
5. **Sync**: New or modified files are sent to the configured destination(s)
6. **Cleanup**: On `stop()` (or context manager exit), watcher thread and connections shut down

The watcher runs as a **daemon thread** — it won't block your notebook or prevent kernel shutdown.

## Security

See [SECURITY.md](SECURITY.md) for the full security policy and vulnerability reporting.

## Known Limitations

- **Polling-based, not instant**: kgout scans the directory every N seconds (default 30). Files won't appear until the next scan completes. Not suitable for real-time streaming.
- **ngrok free tier disconnects after ~2 hours**: This is an ngrok limitation, not a kgout bug. For runs longer than 2 hours, use `gdrive` as your primary destination. kgout will warn you when the tunnel dies.
- **Restricted networks**: ngrok requires outbound internet access on ports 443/4443. Institutional networks (university campuses, corporate firewalls, research lab servers) may block ngrok traffic. If the tunnel fails to start, your network likely blocks it — use the `gdrive` destination instead.
- **Public URL**: Anyone with the ngrok URL can browse and download your files. Don't share it publicly. The URL is random and temporary, but not password-protected.
- **GDrive flat upload**: Subdirectories are flattened into filenames (e.g., `subdir/file.csv` becomes `subdir_file.csv`) in v1.x.
- **Partial file risk**: If a very large file is still being written when a scan occurs, it may sync an incomplete version. kgout waits 2 seconds after last modification (settle time), but for multi-GB files, write to a temp name and rename when complete.
- **No resumable downloads**: If the ngrok tunnel disconnects mid-download, you need to re-download. There's no resume support.
- **Kaggle internet required**: The Kaggle notebook must have internet access enabled (Settings > Internet > On) for both destinations.

## Development

```bash
git clone https://github.com/vybhav72954/kgout
cd kgout
pip install -e ".[dev,all]"
pytest tests/ -v
```

## License

MIT — see [LICENSE](LICENSE)
