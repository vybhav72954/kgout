"""Tests for kgout.destinations.gdrive credential detection."""

import json
import os
import tempfile

try:
    from google.oauth2.credentials import Credentials as _Check
    _HAS_GOOGLE_AUTH = True
except ImportError:
    _HAS_GOOGLE_AUTH = False


def test_detects_oauth2_token():
    """Should detect kgout_oauth2 token type."""
    if not _HAS_GOOGLE_AUTH:
        print("  SKIP (google-auth not installed)")
        return
    from kgout.destinations.gdrive import _load_credentials

    token_data = {
        "type": "kgout_oauth2",
        "token": "fake_access_token",
        "refresh_token": "fake_refresh_token",
        "client_id": "fake_client_id",
        "client_secret": "fake_client_secret",
        "token_uri": "https://oauth2.googleapis.com/token",
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(token_data, f)
        path = f.name

    try:
        creds = _load_credentials(path)
        assert creds.token == "fake_access_token"
        assert creds.refresh_token == "fake_refresh_token"
        assert creds.client_id == "fake_client_id"
    finally:
        os.unlink(path)


def test_detects_authorized_user():
    """Should detect authorized_user token type (standard gcloud format)."""
    if not _HAS_GOOGLE_AUTH:
        print("  SKIP (google-auth not installed)")
        return
    from kgout.destinations.gdrive import _load_credentials

    token_data = {
        "type": "authorized_user",
        "token": "fake_token",
        "refresh_token": "fake_refresh",
        "client_id": "fake_id",
        "client_secret": "fake_secret",
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(token_data, f)
        path = f.name

    try:
        creds = _load_credentials(path)
        assert creds.refresh_token == "fake_refresh"
    finally:
        os.unlink(path)


def test_rejects_unknown_type():
    """Should raise ValueError for unknown credential types."""
    if not _HAS_GOOGLE_AUTH:
        print("  SKIP (google-auth not installed)")
        return
    from kgout.destinations.gdrive import _load_credentials

    token_data = {"type": "something_weird", "token": "x"}

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(token_data, f)
        path = f.name

    try:
        _load_credentials(path)
        raise AssertionError("Should have raised ValueError")
    except ValueError:
        pass  # expected
    finally:
        os.unlink(path)
