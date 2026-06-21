"""Abstract base classes (interfaces) that every component implements.

All cross-component dependencies flow through these interfaces.
Real implementations live in their respective component packages;
fakes live in quorum/fakes/ for isolated development and testing.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from quorum.contracts.models import (
    Claim,
    ConsensusResult,
    ProvenanceRecord,
    TrustScore,
    ValidatorReliability,
    ValidatorResult,
    WorkflowContext,
)

__all__ = [
    "BaseValidator",
    "LLMClient",
    "BaseStore",
    "ValidationPipeline",
    "EventBus",
]


# ---------------------------------------------------------------------------
# Validator interface
# ---------------------------------------------------------------------------


class BaseValidator(ABC):
    """Interface every validator must implement."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique validator name (matches ValidatorName enum values)."""
        ...

    @abstractmethod
    async def validate(self, claim: Claim, context: WorkflowContext) -> ValidatorResult:
        """Validate a claim and return a structured result.

        Args:
            claim: The claim to validate.
            context: Current workflow snapshot with prior accepted claims.

        Returns:
            ValidatorResult with verdict, confidence, evidence, and failure_mode.
        """
        ...


# ---------------------------------------------------------------------------
# LLM client interface (used by consistency and reasoning validators)
# ---------------------------------------------------------------------------


class LLMClient(ABC):
    """Thin interface wrapping an LLM provider."""

    @abstractmethod
    async def complete(
        self,
        system_prompt: str,
        user_message: str,
        *,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> str:
        """Return the model's text completion."""
        ...


# ---------------------------------------------------------------------------
# Store interface
# ---------------------------------------------------------------------------


class BaseStore(ABC):
    """Key–value + list store interface backed by Redis (or a fake)."""

    @abstractmethod
    async def set_json(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        """Serialize value to JSON and store it."""
        ...

    @abstractmethod
    async def get_json(self, key: str) -> Any | None:
        """Retrieve and deserialize a JSON value, or None if missing."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete a key."""
        ...

    @abstractmethod
    async def list_push(self, key: str, value: Any) -> None:
        """Append a JSON-serialized value to a list."""
        ...

    @abstractmethod
    async def list_all(self, key: str) -> list[Any]:
        """Return all items in a list (deserialized from JSON)."""
        ...

    @abstractmethod
    async def list_remove(self, key: str, value: Any) -> None:
        """Remove first matching JSON-serialized value from a list."""
        ...

    @abstractmethod
    async def keys_matching(self, pattern: str) -> list[str]:
        """Return all keys matching a glob pattern."""
        ...

    @abstractmethod
    async def list_trim(self, key: str, start: int, stop: int) -> None:
        """Trim a list so it only contains elements from start to stop (inclusive)."""
        ...


# ---------------------------------------------------------------------------
# Pipeline interface (consumed by the API and uAgent gateway)
# ---------------------------------------------------------------------------


class ValidationPipeline(ABC):
    """Orchestrates validators → consensus → state/provenance/trust."""

    @abstractmethod
    async def process(self, claim: Claim) -> ConsensusResult:
        """Run the full validation pipeline for a claim.

        Side effects:
        - Writes accepted claims to workflow state.
        - Writes provenance record.
        - Updates trust/reliability scores.
        - Quarantines low-confidence claims.
        - Emits ConsensusEvent to the WS broadcast channel.
        """
        ...


# ---------------------------------------------------------------------------
# Event bus interface (for WS broadcasting)
# ---------------------------------------------------------------------------


class EventBus(ABC):
    """Broadcasts real-time consensus events to connected WebSocket clients."""

    @abstractmethod
    async def publish(self, event_dict: dict[str, Any]) -> None:
        """Publish an event to all subscribers."""
        ...

    @abstractmethod
    async def subscribe(self):  # type: ignore[return]
        """Async generator that yields event dicts."""
        ...
