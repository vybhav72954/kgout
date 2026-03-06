# kgout

**Auto-sync Kaggle notebook outputs to Google Drive or your local machine.**

[![PyPI version](https://badge.fury.io/py/kgout.svg)](https://pypi.org/project/kgout/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

When running long ML experiments on Kaggle, kernels can time out or sessions expire — and your output files disappear. **kgout** watches `/kaggle/working/` in the background and automatically syncs new or modified files to Google Drive or exposes them via an ngrok tunnel for instant local download.

Drop it into any notebook as a single cell.

## Install

```bash
# With local/ngrok tunnel support (recommended)
pip install kgout[local]

# With Google Drive support
pip install kgout[gdrive]

# Everything
pip install kgout[all]
```

## Quick Start

### Local Download via ngrok (Recommended)

Exposes your `/kaggle/working/` directory as a public URL — open it in any browser on your phone, laptop, anywhere. Every new file appears instantly.

```python
import os
os.environ["NGROK_AUTH_TOKEN"] = "your_token_here"  # free at ngrok.com

from kgout import KgOut

with KgOut("local") as kg:
    # ┌────────────────────────────────────────────────┐
    # │  kgout — files available at:                   │
    # │  https://abc123.ngrok-free.app                 │
    # └────────────────────────────────────────────────┘

    # ... your training code ...
    # Every new file saved to /kaggle/working/ is instantly
    # browsable and downloadable from the URL above.
    pass
```

**How it works:** kgout starts a file server on localhost, creates an ngrok tunnel to it, and gives you the public URL. The file server serves your watch directory live — any file your notebook saves appears immediately in the browser. A background watcher thread logs every new file and its direct download link.

### Google Drive Auto-Upload

Every new CSV, checkpoint, or plot auto-uploads to a Drive folder the moment it's saved.

```python
from kgout import KgOut

with KgOut(
    "gdrive",
    folder_id="1ABCxyz_your_drive_folder_id",
    credentials="/kaggle/input/my-secrets/service_account.json",
) as kg:
    # ... your training code ...
    pass
```

### Both at Once

```python
with KgOut(
    dest=["local", "gdrive"],
    folder_id="1ABCxyz",
    credentials="/path/to/sa.json",
) as kg:
    pass
```

### Manual start/stop (no context manager)

```python
kg = KgOut("local")
kg.start()

# ... long training ...

print(kg.stats)  # {'files_tracked': 12, 'events_fired': 5}

kg.stop()
```

## Configuration

| Parameter | Default | Description |
|---|---|---|
| `dest` | `"local"` | `"local"`, `"gdrive"`, or `["local", "gdrive"]` |
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

Instead of passing tokens directly, you can set these environment variables:

| Variable | Used by | Description |
|---|---|---|
| `NGROK_AUTH_TOKEN` | `local` destination | ngrok authentication token |
| `KGOUT_GDRIVE_CREDENTIALS` | `gdrive` destination | Path to service account JSON |

See `.env.example` in the repo for a template.

## Default Ignore Patterns

These files are never synced:

- `*.ipynb`, `*.pyc`, `*.tmp`, `*.lock`, `*.log`, `*.swp`, `*.swo`
- `.DS_Store`, `Thumbs.db`
- Hidden files (starting with `.`)
- Directories: `.ipynb_checkpoints`, `__pycache__`, `.git`

Override with `ignore=["*.csv"]` or pass `ignore=[]` to sync everything.

## Setting Up ngrok (for local destination)

1. Create a free account at [ngrok.com](https://ngrok.com)
2. Copy your auth token from [the dashboard](https://dashboard.ngrok.com/get-started/your-authtoken)
3. In your Kaggle notebook:
   ```python
   import os
   os.environ["NGROK_AUTH_TOKEN"] = "your_token"
   ```
   Or pass it directly: `KgOut("local", ngrok_token="your_token")`

**Tip:** On Kaggle, you can store the token as a [Kaggle Secret](https://www.kaggle.com/discussions/product-feedback/114053) and load it with:
```python
from kaggle_secrets import UserSecretsClient
os.environ["NGROK_AUTH_TOKEN"] = UserSecretsClient().get_secret("NGROK_AUTH_TOKEN")
```

## Setting Up Google Drive (for gdrive destination)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project (or use existing) and enable the **Google Drive API**
3. Go to **IAM & Admin > Service Accounts** > Create a service account
4. Create a key (JSON) > download it
5. Upload the JSON to Kaggle as a private dataset (e.g., `my-secrets`)
6. In Google Drive, right-click your target folder > **Share** > paste the service account email (the `client_email` field in the JSON) > give it **Editor** access
7. Copy the folder ID from the Drive URL: `https://drive.google.com/drive/folders/THIS_PART_IS_THE_ID`

## Security

See [SECURITY.md](SECURITY.md) for the full security policy and vulnerability reporting.

## How It Works

1. **Snapshot**: On `start()`, kgout fingerprints all existing files (mtime + size) so they don't trigger syncs
2. **Poll**: A daemon thread scans the watch directory every N seconds
3. **Settle check**: Files modified in the last 2 seconds are skipped (still being written)
4. **Compare**: Each file's fingerprint is compared against the snapshot
5. **Sync**: New or modified files are sent to the configured destination(s)
6. **Cleanup**: On `stop()` (or context manager exit), watcher thread and tunnels shut down

The watcher runs as a **daemon thread** — it won't block your notebook or prevent kernel shutdown.

## Known Limitations

- **Polling-based, not instant**: kgout scans the directory every N seconds (default 30). Files won't appear until the next scan completes. Not suitable for real-time streaming.
- **ngrok free tier**: Limited to 1 tunnel at a time. Sessions may disconnect after ~2 hours. URL changes every time kgout starts.
- **Restricted networks**: ngrok requires outbound internet access on ports 443/4443. Institutional networks (university campuses, corporate firewalls, research lab servers) may block ngrok traffic. If the tunnel fails to start, your network likely blocks it — use the `gdrive` destination instead.
- **Public URL**: Anyone with the ngrok URL can browse and download your files. Don't share it with untrusted parties. The URL is random and temporary, but not password-protected.
- **GDrive flat upload**: Subdirectories are flattened into filenames (e.g., `subdir/file.csv` becomes `subdir_file.csv`) in v1.x.
- **Partial file risk**: If a very large file is still being written when a scan occurs, it may sync an incomplete version. kgout waits 2 seconds after last modification (settle time), but for multi-GB files, write to a temp name and rename when complete.
- **No resumable downloads**: If the ngrok tunnel disconnects mid-download, you need to re-download. There's no resume support.
- **Kaggle internet required**: The Kaggle notebook must have internet access enabled (Settings → Internet → On) for both `local` and `gdrive` destinations.

## Development

```bash
git clone https://github.com/vybhavchaturvedi/kgout
cd kgout
pip install -e ".[dev,all]"
pytest tests/ -v
```

## License

MIT — see [LICENSE](LICENSE)
