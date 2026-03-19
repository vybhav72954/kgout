"""
kgout — Auto-sync Kaggle notebook outputs to Google Drive or local machine.

Usage:
    from kgout import KgOut

    # Auto-upload to Google Drive (recommended)
    kg = KgOut("gdrive", folder_id="...", credentials="...").start()

    # Expose /kaggle/working/ via ngrok tunnel (quick experiments)
    kg = KgOut("local").start()

One-time Google Drive setup (run on your local machine):
    pip install kgout[gdrive]
    kgout-auth
"""

__version__ = "1.2.1"

from kgout.core import KgOut

__all__ = ["KgOut", "__version__"]
