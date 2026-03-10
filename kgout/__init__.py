"""
kgout — Auto-sync Kaggle notebook outputs to Google Drive or local machine.

Usage:
    from kgout import KgOut

    # Auto-upload to Google Drive (recommended for long runs)
    kg = KgOut("gdrive", folder_id="...", credentials="...").start()

    # Expose /kaggle/working/ via ngrok tunnel (for quick experiments)
    kg = KgOut("local").start()
"""

__version__ = "1.1.0"

from kgout.core import KgOut

__all__ = ["KgOut", "__version__"]
