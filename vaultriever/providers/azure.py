"""Azure Key Vault provider (stub).

Intended SRI semantics: ``azure:<vault_or_region>:<secret_name>:<key_or_version>``.
"""

from __future__ import annotations

from typing import Any

from vaultriever.sri import SecretProperties


class AzureSecretProvider:
    """Placeholder provider; not implemented yet."""

    name = 'azure'

    def get_secret_value(self, props: SecretProperties) -> Any:
        raise NotImplementedError('Azure provider not implemented yet.')
