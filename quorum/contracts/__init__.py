"""Shared Pydantic models, interfaces, Redis key builders, config, and errors.

All other components MUST import exclusively from this package.
Never import from sibling components (validators, consensus, state, agents, api).
"""
