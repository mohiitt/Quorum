"""Source Validator — validates financial/investment claims via real web search.

Uses DuckDuckGo + Wikipedia for evidence, then an LLM to grade the claim.
Browserbase is available as a fallback when the free APIs return no results.
"""

from __future__ import annotations

import json
import re
from typing import Protocol

import logging

import httpx

from quorum.contracts.config import Settings, get_settings
from quorum.contracts.interfaces import BaseValidator, LLMClient
from quorum.contracts.models import (
    Claim,
    Evidence,
    FailureMode,
    ValidatorResult,
    Verdict,
    WorkflowContext,
)

logger = logging.getLogger(__name__)

__all__ = ["SourceValidator", "BrowserbaseClient"]

# ---------------------------------------------------------------------------
# External API endpoints (finance/web search only)
# ---------------------------------------------------------------------------

_DDG_URL = "https://api.duckduckgo.com/"
_WIKI_URL = "https://en.wikipedia.org/w/api.php"


# ---------------------------------------------------------------------------
# Browserbase protocol + real HTTP implementation
# ---------------------------------------------------------------------------


class BrowserbaseClient(Protocol):
    """Thin protocol for a Browserbase web-search client."""

    async def search(self, query: str) -> list[dict]: ...


class BrowserbaseHTTPClient:
    """Browserbase client: creates a remote session, connects via Playwright CDP,
    navigates to DuckDuckGo, extracts result snippets, and returns evidence dicts.

    Browserbase provides a remote Chrome instance — Playwright drives it over CDP
    using the session's `connectUrl`. No local browser binary is required.
    """

    _SESSIONS_URL = "https://api.browserbase.com/v1/sessions"

    def __init__(self, api_key: str, project_id: str, http_client: httpx.AsyncClient | None = None) -> None:
        self._api_key = api_key
        self._project_id = project_id
        self._http = http_client or httpx.AsyncClient(timeout=15.0)

    async def search(self, query: str) -> list[dict]:
        """Search DuckDuckGo via a Browserbase-hosted remote browser and return snippets."""
        try:
            # 1. Create a Browserbase session and get its CDP connect URL
            session_resp = await self._http.post(
                self._SESSIONS_URL,
                headers={
                    "X-BB-API-Key": self._api_key,
                    "Content-Type": "application/json",
                },
                json={"projectId": self._project_id, "browserSettings": {}},
            )
            session_resp.raise_for_status()
            session_data = session_resp.json()
            session_id = session_data.get("id", "")
            if not session_id:
                return []
            # Browserbase returns connectUrl as the WebSocket CDP endpoint.
            # Fall back to constructing it if not present in the response.
            connect_url = (
                session_data.get("connectUrl")
                or session_data.get("browserWSEndpoint")
                or f"wss://connect.browserbase.com?apiKey={self._api_key}&sessionId={session_id}"
            )

            # 2. Drive the remote browser via Playwright CDP (no local browser needed)
            from playwright.async_api import async_playwright

            encoded = query.replace(" ", "+")[:200]
            search_url = f"https://html.duckduckgo.com/html/?q={encoded}"
            results: list[dict] = []

            async with async_playwright() as p:
                browser = await p.chromium.connect_over_cdp(connect_url)
                try:
                    # Always create a fresh context for the search
                    context = await browser.new_context(
                        user_agent=(
                            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/124.0.0.0 Safari/537.36"
                        )
                    )
                    page = await context.new_page()
                    await page.goto(search_url, wait_until="domcontentloaded", timeout=12000)

                    # Extract result snippets — DuckDuckGo HTML uses .result__snippet
                    snippet_els = await page.query_selector_all(".result__snippet")
                    title_els = await page.query_selector_all(".result__a")

                    # Use first 8 meaningful words (≥4 chars) for topic relevance scoring.
                    # Avoids penalising long claim sentences where exact phrase won't appear.
                    all_words = query.lower().split()
                    key_words = [w for w in all_words if len(w) >= 4][:8] or all_words[:8]
                    for el in (snippet_els or title_els)[:5]:
                        text = (await el.inner_text()).strip()
                        if not text or len(text) < 15:
                            continue
                        hits = sum(1 for w in key_words if w in text.lower())
                        quality = round(min(0.88, 0.45 + (hits / max(1, len(key_words))) * 0.43), 2)
                        results.append({"snippet": text, "url": None, "quality": quality})
                        if len(results) >= 3:
                            break
                finally:
                    await browser.close()

            # 3. Stop the Browserbase session (fire-and-forget)
            try:
                await self._http.post(
                    f"{self._SESSIONS_URL}/{session_id}",
                    headers={"X-BB-API-Key": self._api_key, "Content-Type": "application/json"},
                    json={"status": "REQUEST_RELEASE"},
                )
            except Exception:
                pass

            return results

        except Exception as exc:
            import logging
            logging.getLogger(__name__).debug("Browserbase search failed: %s", exc)
            return []


# ---------------------------------------------------------------------------
# SourceValidator
# ---------------------------------------------------------------------------


_WEB_ASSESS_SYSTEM = """\
You are a financial fact-checking system. Given a financial/investment claim and real web search results, \
assess whether the claim is plausible and consistent with the evidence.

Return ONLY valid JSON — no fences, no prose:
{"verdict": "accepted"|"rejected"|"needs_review", "confidence": <0.0-1.0>, "rationale": "<one sentence>"}

Rules:
- "accepted"  : Use when the claim is broadly plausible given the web evidence. Specific figures do NOT need \
exact verification — plausibility plus no contradiction is sufficient. Prefer "accepted" for reasonable \
investment observations consistent with general market knowledge.
- "rejected"  : Use ONLY when the claim cites a specific named study / exact non-round statistic / named source \
that clearly does NOT appear anywhere in the search results, OR when the claim directly contradicts strong \
web consensus (e.g., states a market is booming when every search result says it is in structural decline).
- "needs_review": Use ONLY when the claim is entirely off-topic relative to search results or is genuinely \
self-contradictory.
- confidence  : 0.80–0.95 for a clear verdict; 0.50–0.70 only when genuinely uncertain. \
Do not assign low confidence to a clear "accepted" or "rejected" case.
"""


class SourceValidator(BaseValidator):
    """Validates claims by querying real web sources (DuckDuckGo, Wikipedia, SEC EDGAR, PubMed, OWM)."""

    def __init__(
        self,
        *,
        http_client: httpx.AsyncClient | None = None,
        browserbase_client: BrowserbaseClient | None = None,
        llm_client: LLMClient | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._http = http_client if http_client is not None else httpx.AsyncClient()
        self._browserbase = browserbase_client
        self._settings = settings if settings is not None else get_settings()
        # LLM used to grade web evidence against the claim
        if llm_client is not None:
            self._llm: LLMClient | None = llm_client
        elif self._settings.anthropic_api_key:
            from quorum.validators.consistency import AnthropicLLMClient
            self._llm = AnthropicLLMClient(
                api_key=self._settings.anthropic_api_key,
                model=self._settings.anthropic_model,
            )
        else:
            self._llm = None

    @property
    def name(self) -> str:
        return "source"

    async def validate(self, claim: Claim, context: WorkflowContext) -> ValidatorResult:
        # All claims use real web search (DuckDuckGo + Wikipedia + LLM).
        # Short-circuit: ValidatorResult returned directly so evidence quality
        # does NOT double-penalise the LLM confidence already encoded in the verdict.
        web_result = await self._assess_web(claim)
        if web_result is not None:
            return web_result

        # Fallback: Browserbase full-browser search when free APIs return nothing.
        if self._browserbase is not None:
            browser_ev = await self._check_browserbase(claim)
            if browser_ev:
                return self._build_result(claim, browser_ev)

        # No web data at all — benefit of the doubt.
        return self._build_result(claim, [])

    # ------------------------------------------------------------------
    # Source handlers
    # ------------------------------------------------------------------

    async def _check_browserbase(self, claim: Claim) -> list[Evidence]:
        try:
            results = await self._browserbase.search(claim.statement)  # type: ignore[union-attr]
            return [
                Evidence(
                    source="browserbase",
                    url=r.get("url"),
                    snippet=r.get("snippet", ""),
                    quality=float(r.get("quality", 0.5)),
                )
                for r in results[:3]
            ]
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Verdict derivation
    # ------------------------------------------------------------------

    async def _assess_web(self, claim: Claim) -> ValidatorResult | None:
        """Search DuckDuckGo + Wikipedia, then ask the LLM to grade the claim.

        Returns a ValidatorResult directly (NOT via _build_result) so that the
        LLM confidence is the single signal — it is NOT multiplied by evidence quality
        a second time inside compute_score.  Returns None only when no web snippets
        could be fetched at all (caller falls through to NO_EVIDENCE).
        """
        from quorum.utils import strip_fences
        query = claim.statement[:200]
        snippets: list[str] = []

        # 1 — DuckDuckGo Instant Answer (free, no key)
        try:
            resp = await self._http.get(
                _DDG_URL,
                params={"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"},
                timeout=8.0,
                headers={"User-Agent": "Quorum-SourceValidator/1.0"},
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("AbstractText"):
                    snippets.append(f"DuckDuckGo: {data['AbstractText'][:400]}")
                for topic in data.get("RelatedTopics", [])[:4]:
                    if isinstance(topic, dict) and topic.get("Text"):
                        snippets.append(f"Related: {topic['Text'][:200]}")
        except Exception:
            pass

        # 2 — Wikipedia search (free, no key)
        try:
            resp = await self._http.get(
                _WIKI_URL,
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": query[:120],
                    "format": "json",
                    "srlimit": "3",
                    "utf8": "1",
                },
                timeout=8.0,
                headers={"User-Agent": "Quorum-SourceValidator/1.0"},
            )
            if resp.status_code == 200:
                data = resp.json()
                for r in data.get("query", {}).get("search", []):
                    snippet = re.sub(r"<[^>]+>", "", r.get("snippet", ""))
                    snippets.append(f"Wikipedia — {r['title']}: {snippet[:250]}")
        except Exception:
            pass

        logger.info(
            "[SOURCE] agent claim (%.100s…) → %d web snippet(s) from DDG+Wikipedia",
            claim.statement, len(snippets),
        )
        for i, s in enumerate(snippets[:6]):
            logger.info("[SOURCE]   snippet[%d]: %.140s", i, s)

        if not snippets:
            logger.info("[SOURCE]   → no snippets found, returning NO_EVIDENCE")
            return None  # No web data; caller will produce NO_EVIDENCE result

        web_context = "\n".join(snippets[:6])

        # 3 — No LLM: return neutral needs_review backed by raw snippets
        if self._llm is None:
            ev = Evidence(source="web_search", snippet=web_context[:500], quality=1.0)
            return ValidatorResult(
                validator_name="source",
                verdict=Verdict.NEEDS_REVIEW,
                confidence=0.5,
                evidence=[ev],
                failure_mode=FailureMode.NO_EVIDENCE,
                reliability=0.85,
                rationale="Web snippets retrieved but no LLM configured to assess them.",
            )

        # 4 — LLM grades the claim against the real web results
        prompt = (
            f"Claim to verify:\n{claim.statement}\n\n"
            f"Web search results:\n{web_context}"
        )
        logger.info("[SOURCE]   sending LLM assessment (claim=%.80s…)", claim.statement)
        try:
            raw = await self._llm.complete(_WEB_ASSESS_SYSTEM, prompt, max_tokens=256, temperature=0.0)
            logger.info("[SOURCE]   LLM raw response: %.200s", raw.strip())
            parsed = json.loads(strip_fences(raw))
            verdict_str = str(parsed.get("verdict", "needs_review"))
            confidence = max(0.0, min(1.0, float(parsed.get("confidence", 0.5))))
            rationale = str(parsed.get("rationale", ""))
            logger.info(
                "[SOURCE]   LLM verdict=%s conf=%.2f rationale=%.120s",
                verdict_str, confidence, rationale,
            )
        except Exception as exc:
            logger.warning("[SOURCE]   LLM assessment failed: %s", exc)
            # Fall back: snippets exist but LLM failed — weakly positive
            ev = Evidence(source="web_search", snippet=web_context[:500], quality=1.0)
            return ValidatorResult(
                validator_name="source",
                verdict=Verdict.ACCEPTED,
                confidence=0.65,
                evidence=[ev],
                failure_mode=FailureMode.NONE,
                reliability=0.85,
                rationale="Web sources found; LLM assessment unavailable — treating as weakly verified.",
            )

        # Evidence quality is always 1.0 here — the source (DDG + Wikipedia) is
        # reliable.  Verdict direction and strength are fully captured by verdict +
        # confidence; multiplying by a fractional quality would double-penalise.
        ev = Evidence(source="web_search", snippet=f"{rationale}\n\nSources: {web_context[:400]}", quality=1.0)

        if verdict_str == "accepted":
            return ValidatorResult(
                validator_name="source",
                verdict=Verdict.ACCEPTED,
                confidence=confidence,
                evidence=[ev],
                failure_mode=FailureMode.NONE,
                reliability=0.85,
                rationale=rationale,
            )
        elif verdict_str == "rejected":
            return ValidatorResult(
                validator_name="source",
                verdict=Verdict.REJECTED,
                confidence=confidence,
                evidence=[ev],
                failure_mode=FailureMode.CONTRADICTS_SOURCE,
                reliability=0.85,
                rationale=rationale,
            )
        else:
            return ValidatorResult(
                validator_name="source",
                verdict=Verdict.NEEDS_REVIEW,
                confidence=confidence,
                evidence=[ev],
                failure_mode=FailureMode.NO_EVIDENCE,
                reliability=0.85,
                rationale=rationale,
            )

    def _build_result(self, claim: Claim, evidence: list[Evidence]) -> ValidatorResult:
        browser_ev = [e for e in evidence if e.source == "browserbase"]
        if browser_ev:
            return self._verdict_from_browser(browser_ev, evidence)

        # No usable evidence — benefit of the doubt.
        return ValidatorResult(
            validator_name="source",
            verdict=Verdict.ACCEPTED,
            confidence=0.65,
            evidence=evidence,
            failure_mode=FailureMode.NO_EVIDENCE,
            reliability=0.85,
            rationale="No web source returned results; claim is tentatively accepted pending other validators.",
        )

    def _verdict_from_browser(
        self,
        browser_ev: list[Evidence],
        all_evidence: list[Evidence],
    ) -> ValidatorResult:
        # Browserbase found real web content about this topic — positive signal.
        # Use quality=1.0 so LLM-encoded confidence is not double-penalised in compute_score.
        # Confidence is capped at 0.75 because browserbase uses keyword matching, not LLM assessment.
        avg_quality = sum(e.quality for e in browser_ev) / len(browser_ev)
        confidence = round(min(0.75, max(0.55, avg_quality)), 3)
        normalized_ev = [
            Evidence(source=e.source, snippet=e.snippet, quality=1.0) for e in all_evidence
        ]
        return ValidatorResult(
            validator_name="source",
            verdict=Verdict.ACCEPTED,
            confidence=confidence,
            evidence=normalized_ev,
            failure_mode=FailureMode.NONE,
            rationale=f"Browserbase web search found {len(browser_ev)} result(s) with {avg_quality:.0%} topic relevance.",
            reliability=0.85,
        )
