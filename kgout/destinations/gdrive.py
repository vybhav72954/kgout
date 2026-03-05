"""Google Drive destination — auto-uploads files using a service account."""

from __future__ import annotations

import logging
import mimetypes
import os
from typing import Dict, Optional

from kgout.destinations.base import BaseDestination

logger = logging.getLogger("kgout")


class GDriveDestination(BaseDestination):
    """Upload new/modified files to a Google Drive folder.

    Requires a Google Cloud service account with Drive API access.
    The service account's email must have edit access to the target folder.

    Parameters
    ----------
    credentials_path : str
        Path to the service account JSON key file.
    folder_id : str
        Google Drive folder ID (from the folder URL).
    """

    def __init__(self, credentials_path: str, folder_id: str):
        self._creds_path = credentials_path
        self._folder_id = folder_id
        self._service = None
        # Track uploaded file IDs so we can update rather than duplicate
        self._uploaded: Dict[str, str] = {}  # relpath -> drive file ID

    @property
    def name(self) -> str:
        return "gdrive"

    def start(self):
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
        except ImportError:
            raise ImportError(
                "Google Drive dependencies not installed.\n"
                "Install with: pip install kgout[gdrive]"
            )

        if not os.path.isfile(self._creds_path):
            raise FileNotFoundError(
                f"Service account key not found: {self._creds_path}"
            )

        scopes = ["https://www.googleapis.com/auth/drive.file"]
        creds = service_account.Credentials.from_service_account_file(
            self._creds_path, scopes=scopes
        )
        self._service = build("drive", "v3", credentials=creds, cache_discovery=False)

        logger.info(
            "☁️  Google Drive connected → folder %s",
            self._folder_id,
        )

    def stop(self):
        self._service = None

    def _guess_mimetype(self, filepath: str) -> str:
        mime, _ = mimetypes.guess_type(filepath)
        return mime or "application/octet-stream"

    def sync(self, filepath: str, relpath: str, event: str):
        """Upload or update a file in Google Drive."""
        if not self._service:
            logger.error("GDrive service not initialized — skipping %s", relpath)
            return

        # Warn on very large files (>100MB) — these can be slow and eat quota
        try:
            size_mb = os.path.getsize(filepath) / (1024 * 1024)
            if size_mb > 100:
                logger.warning(
                    "⚠️  Large file: %s (%.0f MB) — upload may be slow", relpath, size_mb
                )
        except OSError:
            pass

        from googleapiclient.http import MediaFileUpload

        mime = self._guess_mimetype(filepath)
        media = MediaFileUpload(filepath, mimetype=mime, resumable=True)

        if relpath in self._uploaded and event == "modified":
            # Update existing file
            file_id = self._uploaded[relpath]
            try:
                self._service.files().update(
                    fileId=file_id,
                    media_body=media,
                ).execute()
                logger.info("   ↳ Updated on GDrive: %s", relpath)
            except Exception as exc:
                logger.error("   ↳ GDrive update failed for %s: %s", relpath, exc)
                # Fall through to create
                self._upload_new(filepath, relpath, mime, media)
        else:
            self._upload_new(filepath, relpath, mime, media)

    def _upload_new(self, filepath, relpath, mime, media):
        """Create a new file on Drive."""
        from googleapiclient.http import MediaFileUpload

        # Create a fresh media object — the one passed in may have been
        # consumed by a failed update attempt
        fresh_media = MediaFileUpload(filepath, mimetype=mime, resumable=True)

        metadata = {
            "name": os.path.basename(relpath),
            "parents": [self._folder_id],
        }

        # If relpath has subdirectories, include them in the name
        # (flat upload, no folder creation — keeps it simple for v1)
        if os.sep in relpath or "/" in relpath:
            # Use the full relative path as the filename to avoid collisions
            metadata["name"] = relpath.replace(os.sep, "_").replace("/", "_")

        try:
            result = self._service.files().create(
                body=metadata,
                media_body=fresh_media,
                fields="id,name",
            ).execute()

            self._uploaded[relpath] = result["id"]
            logger.info(
                "   ↳ Uploaded to GDrive: %s (id: %s)",
                result["name"],
                result["id"],
            )
        except Exception as exc:
            logger.error("   ↳ GDrive upload failed for %s: %s", relpath, exc)
