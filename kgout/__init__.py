"""
kgout — Auto-sync Kaggle notebook outputs to Google Drive or local machine.

Usage:
    from kgout import KgOut

    # Expose /kaggle/working/ via ngrok tunnel
    with KgOut("local") as kg:
        # ... your training code ...
        pass

    # Auto-upload new files to Google Drive
    with KgOut("gdrive", folder_id="YOUR_FOLDER_ID") as kg:
        # ... your training code ...
        pass
"""

__version__ = "1.0.1"

from kgout.core import KgOut

__all__ = ["KgOut", "__version__"]
