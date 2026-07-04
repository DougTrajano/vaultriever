"""Databricks secrets provider.

SRI semantics: ``databricks:<profile>:<scope>:<key>``.

- Empty region (``databricks::my-scope:MY_KEY``) -> default workspace: the
    runtime ``dbutils`` when running on Databricks, otherwise the SDK's default
    authentication.
- Non-empty region -> used as the Databricks CLI profile name, e.g.
  ``databricks:staging:my-scope:MY_KEY`` reads via the ``staging`` profile.

Requires the ``databricks`` extra outside a Databricks runtime:
``pip install vaultriever[databricks]``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from vaultriever.exceptions import DatabricksConfigurationError, SecretRetrievalError
from vaultriever.logging import get_logger
from vaultriever.sri import SecretProperties

logger = get_logger(__name__)


@dataclass(frozen=True)
class DatabricksContext:
    """Where to read Databricks secrets from. ``profile=None`` means default."""

    profile: str | None


def resolve_databricks_context(region: str | None) -> DatabricksContext:
    """Map the SRI region component to a Databricks context.

    An empty/None region selects the default workspace; anything else is
    interpreted as a Databricks CLI profile name.
    """
    if not region:
        return DatabricksContext(profile=None)
    return DatabricksContext(profile=region)


def _get_secret(context: DatabricksContext, scope: str, key: str) -> str:
    """Fetch a secret for the given context. Split out so tests can patch it."""
    if context.profile is None:
        # On a Databricks runtime this is the native dbutils; elsewhere the
        # SDK falls back to default authentication.
        try:
            from databricks.sdk.runtime import dbutils

            return str(dbutils.secrets.get(scope=scope, key=key))
        except ImportError:
            try:
                from databricks.sdk import WorkspaceClient
            except ImportError as import_exc:
                raise DatabricksConfigurationError(
                    "databricks-sdk is required for the 'databricks' provider. "
                    'Install with: pip install vaultriever[databricks]'
                ) from import_exc

            client = WorkspaceClient()
            return str(client.dbutils.secrets.get(scope=scope, key=key))

    try:
        from databricks.sdk import WorkspaceClient
    except ImportError as exc:
        raise DatabricksConfigurationError(
            "databricks-sdk is required for the 'databricks' provider. "
            'Install with: pip install vaultriever[databricks]'
        ) from exc
    client = WorkspaceClient(profile=context.profile)
    return str(client.dbutils.secrets.get(scope=scope, key=key))


class DatabricksSecretProvider:
    """Retrieve secrets from Databricks secret scopes."""

    name = 'databricks'

    def get_secret_value(self, props: SecretProperties) -> Any:
        context = resolve_databricks_context(props.region)
        logger.debug(
            'Fetching Databricks secret scope=%r profile=%r', props.secret_name, context.profile
        )
        try:
            return _get_secret(context, props.secret_name, props.secret_key)
        except (SecretRetrievalError, DatabricksConfigurationError):
            raise
        except Exception as exc:
            raise SecretRetrievalError(
                f'Failed to retrieve Databricks secret scope={props.secret_name!r} '
                f'key={props.secret_key!r}: {type(exc).__name__}'
            ) from exc
