"""GCP Secret Manager provider (stub).

Intended SRI semantics: ``gcp:<project_or_region>:<secret_name>:<key_or_version>``.
"""

from __future__ import annotations

from typing import Any

from vaultriever.sri import SecretProperties


class GCPSecretProvider:
    """Placeholder provider; not implemented yet."""

    name = 'gcp'

    def get_secret_value(self, props: SecretProperties) -> Any:
        raise NotImplementedError('GCP provider not implemented yet.')
