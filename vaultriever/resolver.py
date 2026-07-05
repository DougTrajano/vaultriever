"""Secret resolution: parse an SRI and dispatch to the right provider."""

from __future__ import annotations

from vaultriever.logging import get_logger
from vaultriever.providers import SecretProviderRegistry
from vaultriever.sri import parse_sri

logger = get_logger(__name__)


def resolve_secret(secret_sri: str) -> str:
    """Resolve an SRI string to its secret value.

    Raises:
        SRIParseError: If the SRI is malformed.
        ProviderNotRegisteredError: If the provider is unknown.
        SecretRetrievalError: If the provider fails to retrieve the secret.
    """
    props = parse_sri(secret_sri)
    provider = SecretProviderRegistry.get(props.provider)
    logger.debug(
        'Resolving secret via provider=%r qualifier=%r secret_name=%r',
        props.provider,
        props.qualifier,
        props.secret_name,
    )
    value = provider.get_secret_value(props)
    # Always return a string so callers can wrap it in SecretStr.
    return str(value)
