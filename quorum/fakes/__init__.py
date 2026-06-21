"""In-memory fakes and fixtures for isolated development and testing.

Import these instead of real Redis/LLM/validator implementations when
you don't want live external dependencies.
"""

from quorum.fakes.store import FakeStore
from quorum.fakes.validators import FakeValidator, always_accept, always_reject, always_review
from quorum.fakes.llm import FakeLLMClient
from quorum.fakes.fixtures import make_claim, make_workflow_context, make_validator_result
from quorum.fakes.pipeline import FakePipeline
from quorum.fakes.event_bus import FakeEventBus

__all__ = [
    "FakeStore",
    "FakeValidator",
    "always_accept",
    "always_reject",
    "always_review",
    "FakeLLMClient",
    "make_claim",
    "make_workflow_context",
    "make_validator_result",
    "FakePipeline",
    "FakeEventBus",
]
