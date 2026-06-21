"""Shared exception types for the Quorum system."""

from __future__ import annotations


class QuorumError(Exception):
    """Base class for all Quorum errors."""


class ValidationError(QuorumError):
    """Raised when a validator encounters an unrecoverable error."""

    def __init__(self, validator_name: str, message: str) -> None:
        self.validator_name = validator_name
        super().__init__(f"[{validator_name}] {message}")


class ConsensusError(QuorumError):
    """Raised when the consensus engine cannot produce a result."""


class StoreError(QuorumError):
    """Raised when a Redis store operation fails."""


class PipelineError(QuorumError):
    """Raised when the validation pipeline encounters a fatal error."""


class ConfigurationError(QuorumError):
    """Raised for missing or invalid configuration."""
