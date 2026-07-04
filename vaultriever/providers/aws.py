"""AWS Secrets Manager provider.

SRI semantics: ``aws:<region>:<secret_name>:<json_key>``. The secret's
``SecretString`` must be a JSON object; ``json_key`` selects one of its keys.
Credentials are resolved by the AWS SDK default chain (env vars, profile,
IAM role).

Requires the ``aws`` extra: ``pip install vaultriever[aws]``.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from vaultriever.exceptions import SecretRetrievalError
from vaultriever.logging import get_logger
from vaultriever.sri import SecretProperties

logger = get_logger(__name__)


@lru_cache
def _get_aws_secret_json(secret_name: str, region_name: str) -> dict[str, Any]:
    """Fetch and decode a JSON secret, caching by (secret_name, region)."""
    try:
        import boto3
    except ImportError as exc:  # pragma: no cover - depends on install extras
        raise SecretRetrievalError(
            "boto3 is required for the 'aws' provider. Install with: pip install vaultriever[aws]"
        ) from exc

    logger.debug('Fetching AWS secret %r in region %r', secret_name, region_name)
    client = boto3.Session().client('secretsmanager', region_name=region_name)
    try:
        response = client.get_secret_value(SecretId=secret_name)
    except Exception as exc:
        raise SecretRetrievalError(
            f'Failed to retrieve AWS secret {secret_name!r} in region {region_name!r}: '
            f'{type(exc).__name__}'
        ) from exc

    secret_string = response.get('SecretString')
    if secret_string is None:
        raise SecretRetrievalError(
            f'AWS secret {secret_name!r} has no SecretString (binary secrets are not supported)'
        )
    try:
        data = json.loads(secret_string)
    except json.JSONDecodeError as exc:
        raise SecretRetrievalError(f'AWS secret {secret_name!r} is not valid JSON') from exc
    if not isinstance(data, dict):
        raise SecretRetrievalError(f'AWS secret {secret_name!r} is not a JSON object')
    return data


class AWSSecretProvider:
    """Retrieve keys from JSON secrets stored in AWS Secrets Manager."""

    name = 'aws'

    def get_secret_value(self, props: SecretProperties) -> Any:
        if not props.region:
            raise SecretRetrievalError(
                "AWS SRIs require a non-empty region, e.g. 'aws:us-east-1:my-secret:MY_KEY'"
            )
        data = _get_aws_secret_json(props.secret_name, props.region)
        try:
            return data[props.secret_key]
        except KeyError:
            raise SecretRetrievalError(
                f'Key {props.secret_key!r} not found in AWS secret {props.secret_name!r}'
            ) from None

    @staticmethod
    def clear_cache() -> None:
        """Clear the cached secret payloads (e.g. after rotation)."""
        _get_aws_secret_json.cache_clear()
