"""Base exceptions for the ``eidosxr`` package."""

from __future__ import annotations


class EidosError(Exception):
    """Base class for eidos exceptions."""


class EidosSpecError(EidosError):
    """Base class for eidos spec exceptions."""
