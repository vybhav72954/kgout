"""
kgout-auth — One-time Google Drive authentication.

Run this on your LOCAL machine (not on Kaggle):

    pip install kgout[gdrive]
    kgout-auth --client-secrets /path/to/client_secrets.json

How to get client_secrets.json:
    1. Go to https://console.cloud.google.com/apis/credentials
    2. Click "Create Credentials" → "OAuth client ID"
    3. Application type: "Desktop app"
    4. Download the JSON file

This opens a browser, you log into Google, and it saves a token file.
Upload that token file to Kaggle as a private dataset.
"""

from __future__ import annotations

import json
import os
import sys

_SCOPES = ["https://www.googleapis.com/auth/drive.file"]
_DEFAULT_TOKEN_PATH = "kgout_token.json"


def _run_auth(client_secrets_path: str, output_path: str = _DEFAULT_TOKEN_PATH):
    """Run the OAuth2 flow and save credentials to a JSON file."""
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("ERROR: google-auth-oauthlib is required for authentication.")
        print("Install with: pip install kgout[gdrive]")
        sys.exit(1)

    if not os.path.isfile(client_secrets_path):
        print(f"ERROR: Client secrets file not found: {client_secrets_path}")
        print()
        print("How to create it:")
        print("  1. Go to https://console.cloud.google.com/apis/credentials")
        print("  2. Click 'Create Credentials' → 'OAuth client ID'")
        print("  3. Application type: 'Desktop app'")
        print("  4. Download the JSON file")
        print()
        print("Then run: kgout-auth --client-secrets /path/to/downloaded.json")
        sys.exit(1)

    print()
    print("=" * 56)
    print("  kgout — Google Drive Authentication")
    print("=" * 56)
    print()
    print("  A browser window will open.")
    print("  Log into your Google account and grant Drive access.")
    print("  This is a one-time setup.")
    print()

    flow = InstalledAppFlow.from_client_secrets_file(client_secrets_path, _SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent")

    # Save token as a portable JSON that works on Kaggle
    # without needing google-auth-oauthlib installed there.
    # Only google-auth (included in gdrive extras) is needed to refresh.
    token_data = {
        "type": "kgout_oauth2",
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "token_uri": creds.token_uri,
    }

    with open(output_path, "w") as f:
        json.dump(token_data, f, indent=2)

    abs_path = os.path.abspath(output_path)
    print(f"  Token saved to: {abs_path}")
    print()
    print("  Next steps:")
    print("  1. Upload this file to Kaggle as a PRIVATE dataset")
    print("     (e.g., name it 'kgout-credentials')")
    print("  2. In your Kaggle notebook:")
    print()
    print("     from kgout import KgOut")
    print("     kg = KgOut(")
    print('         folder_id="YOUR_DRIVE_FOLDER_ID",')
    print(f'         credentials="/kaggle/input/kgout-credentials/{output_path}",')
    print("     ).start()")
    print()
    print("=" * 56)
    print()


def main():
    """Entry point for the kgout-auth CLI command."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="kgout-auth",
        description=(
            "One-time Google Drive authentication for kgout.\n\n"
            "Creates a token file that you upload to Kaggle.\n"
            "Requires a client_secrets.json from Google Cloud Console."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--client-secrets", type=str, required=True,
        metavar="PATH",
        help="Path to your OAuth2 client_secrets.json from Google Cloud Console.",
    )
    parser.add_argument(
        "--output", type=str, default=_DEFAULT_TOKEN_PATH,
        metavar="PATH",
        help=f"Where to save the token file (default: {_DEFAULT_TOKEN_PATH}).",
    )
    args = parser.parse_args()

    _run_auth(client_secrets_path=args.client_secrets, output_path=args.output)


if __name__ == "__main__":
    main()
