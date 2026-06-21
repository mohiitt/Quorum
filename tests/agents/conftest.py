"""pytest configuration for agents tests.

uAgents' Agent.__init__ calls asyncio.get_event_loop_policy().get_event_loop(),
which raises RuntimeError in Python 3.14+ when no current event loop exists.
The fixture below ensures each test has a running event loop.
"""

import asyncio

import pytest


@pytest.fixture(autouse=True)
def event_loop_for_uagents():
    """Create and set a new event loop for the duration of each test."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()
    asyncio.set_event_loop(None)
