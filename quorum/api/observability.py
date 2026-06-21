"""Sentry and Arize observability wrappers.

All functions are no-ops when keys are not configured — safe to call unconditionally.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_sentry_initialized = False
_arize_client = None


def init_sentry(dsn: str) -> None:
    global _sentry_initialized
    if not dsn:
        return
    try:
        import sentry_sdk
        sentry_sdk.init(
            dsn=dsn,
            traces_sample_rate=0.1,
            environment="production",
        )
        _sentry_initialized = True
        logger.info("Sentry initialized")
    except Exception as exc:
        logger.warning("Sentry init failed: %s", exc)


def _get_arize_client():
    global _arize_client
    if _arize_client is not None:
        return _arize_client
    try:
        from quorum.contracts.config import get_settings
        settings = get_settings()
        # Skip if keys are missing or still placeholder "..."
        if (
            not settings.arize_api_key
            or not settings.arize_space_key
            or settings.arize_api_key.strip(".") == ""
            or settings.arize_space_key.strip(".") == ""
        ):
            return None
        # Arize SDK (new API — ArizeClient lives at package root)
        from arize import ArizeClient  # type: ignore[attr-defined]
        _arize_client = ArizeClient(
            api_key=settings.arize_api_key,
            space_key=settings.arize_space_key,
        )
        return _arize_client
    except Exception as exc:
        logger.debug("Arize client init skipped: %s", exc)
        return None


def capture_validation_failure(claim_id: str, validator: str, error: str) -> None:
    if not _sentry_initialized:
        return
    try:
        import sentry_sdk
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("claim_id", claim_id)
            scope.set_tag("validator", validator)
            sentry_sdk.capture_message(
                f"Validation failure [{validator}]: {error}",
                level="warning",
            )
    except Exception as exc:
        logger.debug("Sentry capture failed: %s", exc)


def capture_consensus_failure(claim_id: str, error: str) -> None:
    if not _sentry_initialized:
        return
    try:
        import sentry_sdk
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("claim_id", claim_id)
            sentry_sdk.capture_message(
                f"Consensus failure: {error}",
                level="error",
            )
    except Exception as exc:
        logger.debug("Sentry capture failed: %s", exc)


def log_validator_result_to_arize(
    validator_name: str,
    verdict: str,
    confidence: float,
    claim_id: str,
) -> None:
    client = _get_arize_client()
    if client is None:
        return
    try:
        from arize.utils.types import ModelTypes, Environments
        from quorum.contracts.config import get_settings
        settings = get_settings()
        client.log(
            model_id=settings.arize_model_id,
            model_type=ModelTypes.SCORE_CATEGORICAL,
            environment=Environments.PRODUCTION,
            model_version="0.1.0",
            prediction_id=f"{claim_id}:{validator_name}",
            prediction_label=verdict,
            prediction_score=confidence,
        )
    except Exception as exc:
        logger.debug("Arize log failed: %s", exc)
