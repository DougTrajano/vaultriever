"""GCP Secret Manager provider.

SRI semantics: ``gcp:<project_id>:<secret_name>:<version>``. ``version`` is
either the literal ``latest`` or a specific secret version number.
Credentials are resolved via Application Default Credentials (ADC).

Requires the ``gcp`` extra: ``pip install vaultriever[gcp]``.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from vaultriever.exceptions import SecretRetrievalError
from vaultriever.logging import get_logger
from vaultriever.sri import SecretProperties

logger = get_logger(__name__)


@lru_cache
def _get_gcp_secret_value(project_id: str, secret_name: str, version: str) -> str:
    """Fetch a Secret Manager value, caching by (project_id, secret_name, version)."""
    try:
        from google.cloud import secretmanager
    except ImportError as exc:
        raise SecretRetrievalError(
            "google-cloud-secret-manager is required for the 'gcp' provider. "
            'Install with: pip install vaultriever[gcp]'
        ) from exc

    name = f'projects/{project_id}/secrets/{secret_name}/versions/{version}'
    logger.debug('Fetching GCP secret %r in project %r', secret_name, project_id)
    client = secretmanager.SecretManagerServiceClient()
    try:
        response = client.access_secret_version(request={'name': name})
    except Exception as exc:
        raise SecretRetrievalError(
            f'Failed to retrieve GCP secret {secret_name!r} in project {project_id!r}: '
            f'{type(exc).__name__}'
        ) from exc
    return response.payload.data.decode('UTF-8')


class GCPSecretProvider:
    """Retrieve secret values from GCP Secret Manager."""

    name = 'gcp'

    def get_secret_value(self, props: SecretProperties) -> Any:
        if not props.region:
            raise SecretRetrievalError(
                "GCP SRIs require a non-empty project id, e.g. 'gcp:my-project:my-secret:latest'"
            )
        return _get_gcp_secret_value(props.region, props.secret_name, props.secret_key)

    @staticmethod
    def clear_cache() -> None:
        """Clear the cached secret values (e.g. after rotation)."""
        _get_gcp_secret_value.cache_clear()
