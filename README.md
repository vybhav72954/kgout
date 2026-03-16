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

### Google Drive (Recommended)

Works for runs of any length. Survives session disconnects. Files auto-upload the moment they're saved.

**One-time setup (5 minutes, on your local machine):**

```bash
pip install kgout[gdrive]
kgout-auth --client-secrets /path/to/client_secrets.json
```

This opens a browser, you log into Google, and it saves `kgout_token.json`. Upload that file to Kaggle as a private dataset.

> **How to get `client_secrets.json`:**
> 1. Go to [Google Cloud Console → Credentials](https://console.cloud.google.com/apis/credentials)
> 2. Click **Create Credentials → OAuth client ID**
> 3. Application type: **Desktop app**
> 4. Download the JSON

**In your Kaggle notebook:**

```python
!pip install kgout[gdrive] -q

from kgout import KgOut
kg = KgOut(
    folder_id="1aBcDeFgHiJkLmNoPqRsTuVwXyZ",  # from Drive folder URL
    credentials="/kaggle/input/kgout-credentials/kgout_token.json",
).start()

# ... your training code ...
# Every new file auto-uploads to Google Drive.
# No kg.stop() needed — uploads continue until the kernel ends.
```

### Local Download via ngrok

Exposes `/kaggle/working/` as a browsable URL. Good for quick experiments.

```python
import os
os.environ["NGROK_AUTH_TOKEN"] = "your_token"  # free at ngrok.com

from kgout import KgOut
kg = KgOut("local").start()
# Open the printed URL in your browser.
# ⚠️  ngrok free tier: tunnel disconnects after ~2 hours.
```

### Both at Once

Google Drive for persistence, ngrok for instant browsing while it lasts:

```python
kg = KgOut(
    dest=["gdrive", "local"],
    folder_id="1aBcDeFgHiJkLmNoPqRsTuVwXyZ",
    credentials="/kaggle/input/kgout-credentials/kgout_token.json",
).start()
```

### Context manager vs manual start

```python
# ✅ RECOMMENDED — stays alive after training ends
kg = KgOut(...).start()
train_model()
# ← still running, download/upload continues
# kg.stop()  # only call when you're truly done

# ⚠️  Context manager — STOPS when the block ends
with KgOut(...) as kg:
# ⚠️  Context manager — STOPS when the block ends
with KgOut(...) as kg:
    train_model()
# ← dead here, no more syncing
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
**For Kaggle, always use `.start()`**. The context manager kills everything when your code finishes.

## Setting Up Google Drive

### Step 1: Create OAuth2 Credentials (one-time)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project (or use existing) and **enable the Google Drive API**
3. Go to **APIs & Services → Credentials**
4. Click **Create Credentials → OAuth client ID**
5. Application type: **Desktop app** → Create
6. Download the JSON (this is your `client_secrets.json`)

### Step 2: Generate Token (one-time, on your local machine)

```bash
pip install kgout[gdrive]
kgout-auth --client-secrets /path/to/client_secrets.json
```

A browser opens. Log in with your Google account and grant access. A file called `kgout_token.json` is saved.

### Step 3: Upload Token to Kaggle

1. Go to https://www.kaggle.com/datasets/new
2. Name: `kgout-credentials` → make it **Private**
3. Upload `kgout_token.json` → Create

### Step 4: Get Your Folder ID

In Google Drive, create a folder for outputs. The folder ID is in the URL:

```
https://drive.google.com/drive/folders/1aBcDeFgHiJkLmNoPqRsTuVwXyZ
                                        └──── this is folder_id ────┘
```

### Step 5: Use in Notebook

```python
!pip install kgout[gdrive] -q

from kgout import KgOut
kg = KgOut(
    folder_id="1aBcDeFgHiJkLmNoPqRsTuVwXyZ",
    credentials="/kaggle/input/kgout-credentials/kgout_token.json",
).start()
```

Done. Every file saved to `/kaggle/working/` auto-uploads to your Drive folder.

### Service Accounts (Alternative)

Service accounts still work for **Google Workspace Shared Drives**. If you have a Workspace account (university, company), you can use a service account JSON directly:

```python
kg = KgOut(
    folder_id="SHARED_DRIVE_FOLDER_ID",
    credentials="/kaggle/input/my-creds/service_account.json",
).start()
```

**Note:** Service accounts cannot upload to regular (personal) Google Drive folders — Google returns `storageQuotaExceeded`. Use OAuth2 credentials for personal Drive.

## Setting Up ngrok

1. Create a free account at [ngrok.com](https://ngrok.com)
2. Copy your auth token from [the dashboard](https://dashboard.ngrok.com/get-started/your-authtoken)
3. In your notebook:
   ```python
   import os
   os.environ["NGROK_AUTH_TOKEN"] = "your_token"
   ```

**Tip:** Store the token as a [Kaggle Secret](https://www.kaggle.com/discussions/product-feedback/114053):
```python
from kaggle_secrets import UserSecretsClient
os.environ["NGROK_AUTH_TOKEN"] = UserSecretsClient().get_secret("NGROK_AUTH_TOKEN")
```

## Configuration

| Parameter | Default | Description |
|---|---|---|
| `dest` | `"gdrive"` | `"gdrive"`, `"local"`, or `["gdrive", "local"]` |
| `dest` | `"gdrive"` | `"gdrive"`, `"local"`, or `["gdrive", "local"]` |
| `watch_dir` | `/kaggle/working` | Directory to watch (recursive) |
| `interval` | `30` | Seconds between scans (min: 5) |
| `ignore` | see below | Glob patterns for files to skip |
| `snapshot_existing` | `True` | If True, skip files that exist before `start()` |
| `folder_id` | — | Google Drive folder ID |
| `credentials` | — | Path to credentials JSON (OAuth2 token or service account) |
| `ngrok_token` | — | ngrok auth token |
| `port` | `8384` | Local file server port |
| `verbose` | `True` | Enable logging output |

### Environment Variables

| Variable | Description |
|---|---|
| `KGOUT_GDRIVE_FOLDER_ID` | Google Drive folder ID |
| `KGOUT_GDRIVE_CREDENTIALS` | Path to credentials JSON |
| `NGROK_AUTH_TOKEN` | ngrok authentication token |

## Default Ignore Patterns

These files are never synced: `*.ipynb`, `*.pyc`, `*.tmp`, `*.lock`, `*.log`, `*.swp`, `*.swo`, `.DS_Store`, `Thumbs.db`, hidden files (starting with `.`), and directories `.ipynb_checkpoints`, `__pycache__`, `.git`.

Override with `ignore=["*.csv"]` or pass `ignore=[]` to sync everything.

## How It Works

1. **Snapshot**: On `start()`, kgout fingerprints all existing files so they don't trigger syncs
2. **Poll**: A daemon thread scans the watch directory every N seconds
3. **Settle check**: Files modified in the last 2 seconds are skipped (still being written)
4. **Compare**: Each file's fingerprint is compared against the snapshot
5. **Sync**: New or modified files are sent to the configured destination(s)
6. **Cleanup**: On `stop()`, watcher thread and connections shut down

## Known Limitations

- **Polling-based, not instant**: Scans every N seconds (default 30). Not real-time.
- **ngrok free tier disconnects after ~2 hours**: Use `gdrive` for long runs. kgout warns when the tunnel dies.
- **Restricted networks**: University/corporate firewalls may block ngrok. Use `gdrive` instead.
- **Public ngrok URL**: Anyone with the URL can download your files. Don't share it.
- **GDrive flat upload**: Subdirectories are flattened to filenames (e.g., `subdir/file.csv` → `subdir_file.csv`).
- **Partial file risk**: For multi-GB files, write to a temp name and rename when complete.
- **Kaggle internet required**: Settings → Internet → On.

## Security

See [SECURITY.md](SECURITY.md) for the full security policy.

## Development

```bash
git clone https://github.com/vybhav72954/kgout
git clone https://github.com/vybhav72954/kgout
cd kgout
pip install -e ".[dev,all]"
pytest tests/ -v
```

## License

MIT — see [LICENSE](LICENSE)
