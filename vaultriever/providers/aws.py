"""AWS Secrets Manager provider.

SRI semantics: ``aws:<region>:<secret_name>:<json_key>``.

- If the secret's ``SecretString`` is a JSON object, ``json_key`` is required
  and selects one of its keys.
- If the secret is plaintext (not a JSON object), ``json_key`` must be
  omitted (``aws:<region>:<secret_name>:``) and the whole ``SecretString`` is
  returned as-is.

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
def _get_aws_secret_string(secret_name: str, region_name: str) -> str:
    """Fetch the raw secret string, caching by (secret_name, region)."""
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
    return secret_string


class AWSSecretProvider:
    """Retrieve values from AWS Secrets Manager, as JSON keys or plaintext."""

    name = 'aws'

    def get_secret_value(self, props: SecretProperties) -> Any:
        if not props.qualifier:
            raise SecretRetrievalError(
                "AWS SRIs require a non-empty region, e.g. 'aws:us-east-1:my-secret:MY_KEY'"
            )
        secret_string = _get_aws_secret_string(props.secret_name, props.qualifier)
        try:
            data = json.loads(secret_string)
        except json.JSONDecodeError:
            data = None
        if not isinstance(data, dict):
            if props.secret_key is not None:
                raise SecretRetrievalError(
                    f'AWS secret {props.secret_name!r} is not JSON-based; omit the secret_key '
                    f"segment for plaintext secrets, e.g. 'aws:{props.qualifier}:"
                    f"{props.secret_name}:'"
                )
            return secret_string
        if props.secret_key is None:
            raise SecretRetrievalError(
                f'AWS secret {props.secret_name!r} is a JSON object; secret_key is required to '
                f'select a key'
            )
        try:
            return data[props.secret_key]
        except KeyError:
            raise SecretRetrievalError(
                f'Key {props.secret_key!r} not found in AWS secret {props.secret_name!r}'
            ) from None

    @staticmethod
    def clear_cache() -> None:
        """Clear the cached secret payloads (e.g. after rotation)."""
        _get_aws_secret_string.cache_clear()
