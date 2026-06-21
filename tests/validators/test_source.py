"""Tests for the Source Validator (finance/web-search MVP)."""

from __future__ import annotations

import pytest
import respx
import httpx

from quorum.contracts.interfaces import BaseValidator
from quorum.contracts.models import FailureMode, Verdict
from quorum.contracts.config import Settings
from quorum.fakes.fixtures import make_claim, make_workflow_context
from quorum.validators.source import SourceValidator


def _make_settings(**kwargs) -> Settings:
    defaults = {
        "REDIS_URL": "redis://localhost:6379/0",
        "ANTHROPIC_API_KEY": "",
        "SENTRY_DSN": "",
        "ARIZE_API_KEY": "",
        "ARIZE_SPACE_KEY": "",
        "BROWSERBASE_API_KEY": "",
        "BROWSERBASE_PROJECT_ID": "",
        "OPENWEATHER_API_KEY": "",
        "PUBMED_API_KEY": "",
    }
    defaults.update(kwargs)
    return Settings(**{k.lower(): v for k, v in defaults.items()})


class TestSourceValidatorBasics:
    def test_implements_base_validator(self):
        v = SourceValidator(settings=_make_settings())
        assert isinstance(v, BaseValidator)
        assert v.name == "source"

    async def test_no_web_results_no_evidence_fallback(self):
        """Both DDG and Wikipedia error → NO_EVIDENCE fallback → ACCEPTED/0.65."""
        async with respx.mock(assert_all_called=False) as mock:
            mock.get("https://api.duckduckgo.com/").mock(return_value=httpx.Response(500))
            mock.get("https://en.wikipedia.org/w/api.php").mock(return_value=httpx.Response(500))
            async with httpx.AsyncClient() as http:
                validator = SourceValidator(http_client=http, settings=_make_settings())
                claim = make_claim(statement="Should I invest in renewable energy stocks?")
                result = await validator.validate(claim, make_workflow_context())
        assert result.failure_mode == FailureMode.NO_EVIDENCE
        assert result.verdict == Verdict.ACCEPTED
        assert result is not None


class TestWebSearchValidation:
    async def test_ddg_wikipedia_returns_accepted_for_reasonable_claim(self):
        """DuckDuckGo + Wikipedia + LLM → ACCEPTED; evidence quality=1.0 (no double-penalty)."""
        from quorum.fakes import FakeLLMClient

        ddg_resp = {
            "AbstractText": "Renewable energy stocks have shown steady growth driven by policy support.",
            "RelatedTopics": [{"Text": "Solar investment grew 20% in 2023 per IEA data."}],
        }
        wiki_resp = {
            "query": {
                "search": [
                    {"title": "Renewable energy", "snippet": "Renewable energy investment has accelerated globally."}
                ]
            }
        }
        llm = FakeLLMClient(response='{"verdict":"accepted","confidence":0.82,"rationale":"Claim aligns with broadly available investment data."}')

        async with respx.mock(assert_all_called=False) as mock:
            mock.get("https://api.duckduckgo.com/").mock(return_value=httpx.Response(200, json=ddg_resp))
            mock.get("https://en.wikipedia.org/w/api.php").mock(return_value=httpx.Response(200, json=wiki_resp))
            async with httpx.AsyncClient() as http:
                validator = SourceValidator(http_client=http, llm_client=llm, settings=_make_settings())
                claim = make_claim(statement="Renewable energy stocks have shown strong growth in recent years.")
                result = await validator.validate(claim, make_workflow_context())

        assert result.verdict == Verdict.ACCEPTED
        assert result.confidence == 0.82
        assert any(e.source == "web_search" for e in result.evidence)
        # Evidence quality must be 1.0 — confidence must NOT be encoded twice
        assert all(e.quality == 1.0 for e in result.evidence if e.source == "web_search")

    async def test_fabricated_claim_gets_rejected(self):
        """LLM detects fabricated stats not found in web results → REJECTED."""
        from quorum.fakes import FakeLLMClient

        ddg_resp = {"AbstractText": "Coal stocks face long-term headwinds from energy transition.", "RelatedTopics": []}
        wiki_resp = {"query": {"search": [{"title": "Coal", "snippet": "Coal industry declining due to renewables."}]}}
        llm = FakeLLMClient(response='{"verdict":"rejected","confidence":0.88,"rationale":"Cited BloombergNEF study with 28.7% figure not found in any search results."}')

        async with respx.mock(assert_all_called=False) as mock:
            mock.get("https://api.duckduckgo.com/").mock(return_value=httpx.Response(200, json=ddg_resp))
            mock.get("https://en.wikipedia.org/w/api.php").mock(return_value=httpx.Response(200, json=wiki_resp))
            async with httpx.AsyncClient() as http:
                validator = SourceValidator(http_client=http, llm_client=llm, settings=_make_settings())
                claim = make_claim(statement="A BloombergNEF study found coal stocks outperformed by 28.7% in 2024.")
                result = await validator.validate(claim, make_workflow_context())

        assert result.verdict == Verdict.REJECTED
        assert result.failure_mode == FailureMode.CONTRADICTS_SOURCE
        assert result.confidence == 0.88

    async def test_web_search_no_results_returns_no_evidence(self):
        """If both DDG and Wikipedia fail, _assess_web returns None → NO_EVIDENCE fallback."""
        async with respx.mock(assert_all_called=False) as mock:
            mock.get("https://api.duckduckgo.com/").mock(return_value=httpx.Response(500, text="err"))
            mock.get("https://en.wikipedia.org/w/api.php").mock(return_value=httpx.Response(500, text="err"))
            async with httpx.AsyncClient() as http:
                validator = SourceValidator(http_client=http, settings=_make_settings())
                claim = make_claim(statement="Should I invest in renewable energy stocks?")
                result = await validator.validate(claim, make_workflow_context())
        assert result.failure_mode == FailureMode.NO_EVIDENCE

    async def test_web_search_no_llm_returns_needs_review(self):
        """Without LLM, web snippets are retrieved but can't be graded → NEEDS_REVIEW."""
        ddg_resp = {"AbstractText": "Investment information.", "RelatedTopics": []}
        async with respx.mock(assert_all_called=False) as mock:
            mock.get("https://api.duckduckgo.com/").mock(return_value=httpx.Response(200, json=ddg_resp))
            mock.get("https://en.wikipedia.org/w/api.php").mock(return_value=httpx.Response(200, json={"query": {"search": []}}))
            async with httpx.AsyncClient() as http:
                validator = SourceValidator(http_client=http, llm_client=None, settings=_make_settings())
                claim = make_claim(statement="Should I invest in gold futures?")
                result = await validator.validate(claim, make_workflow_context())
        assert result.verdict == Verdict.NEEDS_REVIEW
        assert any(e.source == "web_search" for e in result.evidence)
        assert all(e.quality == 1.0 for e in result.evidence if e.source == "web_search")


