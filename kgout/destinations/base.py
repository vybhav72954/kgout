"""Abstract base class for sync destinations."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseDestination(ABC):
    """Interface that all destinations implement."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name for logging."""

    def start(self):
        """Called when kgout starts. Override for setup (e.g. tunnel)."""

    def stop(self):
        """Called when kgout stops. Override for cleanup."""

    @abstractmethod
    def sync(self, filepath: str, relpath: str, event: str):
        """Sync a single file.

        Parameters
        ----------
        filepath : str
            Absolute path to the file.
        relpath : str
            Path relative to the watch directory.
        event : str
            ``"created"`` or ``"modified"``.
        """
