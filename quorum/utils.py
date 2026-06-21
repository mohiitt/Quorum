"""Shared utilities used across the quorum package."""

from __future__ import annotations

import re


def strip_fences(text: str) -> str:
    """Extract the JSON payload from an LLM response, stripping markdown code fences.

    Handles cases where the model adds text before/after the closing fence.
    Falls back to extracting the outermost { } block if no fences are present.
    """
    text = text.strip()
    # Extract content between ```(json)? ... ``` using DOTALL for multi-line
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if m:
        return m.group(1).strip()
    # No fences — extract outermost JSON object { }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text
