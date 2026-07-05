"""Azure Key Vault provider.

SRI semantics: ``azure:<vault_name>:<secret_name>:<version>``. ``version`` is
either the literal ``latest`` or a specific Key Vault secret version id.
Credentials are resolved via ``DefaultAzureCredential`` (environment
variables, managed identity, Azure CLI, etc.).

Requires the ``azure`` extra: ``pip install vaultriever[azure]``.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from vaultriever.exceptions import SecretRetrievalError
from vaultriever.logging import get_logger
from vaultriever.sri import SecretProperties

logger = get_logger(__name__)


@lru_cache
def _get_azure_secret_value(vault_name: str, secret_name: str, version: str) -> str:
    """Fetch a Key Vault secret value, caching by (vault_name, secret_name, version)."""
    try:
        from azure.identity import DefaultAzureCredential
        from azure.keyvault.secrets import SecretClient
    except ImportError as exc:
        raise SecretRetrievalError(
            "azure-identity and azure-keyvault-secrets are required for the 'azure' "
            'provider. Install with: pip install vaultriever[azure]'
        ) from exc

    vault_url = f'https://{vault_name}.vault.azure.net/'
    logger.debug('Fetching Azure secret %r from vault %r', secret_name, vault_name)
    client = SecretClient(vault_url=vault_url, credential=DefaultAzureCredential())
    try:
        secret = (
            client.get_secret(secret_name)
            if version.lower() == 'latest'
            else client.get_secret(secret_name, version=version)
        )
    except Exception as exc:
        raise SecretRetrievalError(
            f'Failed to retrieve Azure secret {secret_name!r} from vault {vault_name!r}: '
            f'{type(exc).__name__}'
        ) from exc
    return str(secret.value)


class AzureSecretProvider:
    """Retrieve secret values from Azure Key Vault."""

    name = 'azure'

    def get_secret_value(self, props: SecretProperties) -> Any:
        if not props.qualifier:
            raise SecretRetrievalError(
                "Azure SRIs require a non-empty vault name, e.g. 'azure:my-vault:my-secret:latest'"
            )
        return _get_azure_secret_value(props.qualifier, props.secret_name, props.secret_key)

    @staticmethod
    def clear_cache() -> None:
        """Clear the cached secret values (e.g. after rotation)."""
        _get_azure_secret_value.cache_clear()
