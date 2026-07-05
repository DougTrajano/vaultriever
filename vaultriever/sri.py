"""Secret Resource Identifier (SRI) parsing and validation.

Canonical format::

    provider:qualifier:secret_name:secret_key

The ``qualifier`` segment is provider-defined: an AWS region, a Databricks
CLI profile, an Azure Key Vault name, a GCP project id, etc.

Examples:
    - ``aws:us-east-1:my-secret:OPENAI_API_KEY``
    - ``databricks::my-secret-scope:OPENAI_API_KEY`` (empty qualifier ->
      default profile/workspace)
    - ``aws:us-east-1:my-plain-secret:`` (empty secret_key -> provider-defined
      default, e.g. a plaintext AWS secret)
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from vaultriever.exceptions import SRIParseError

SRI_PARTS = 4
_PROVIDER_RE = re.compile(r'^[a-z][a-z0-9_-]*$')
# Qualifiers (regions, profiles, vault names, project ids, ...) are
# identifier-like. Keeping this strict prevents strings such as
# 'postgresql://user:pass@host:5432/db' from being detected as SRIs.
_QUALIFIER_RE = re.compile(r'^[A-Za-z0-9._-]*$')

_FORMAT_HINT = "Expected 'provider:qualifier:secret_name:secret_key'"


@dataclass(frozen=True)
class SecretProperties:
    """Parsed components of an SRI string."""

    provider: str
    qualifier: str | None
    secret_name: str
    secret_key: str | None


def is_sri(value: str) -> bool:
    """Return True if ``value`` is structurally a valid SRI.

    The check requires exactly 4 colon-separated parts, a lowercase provider
    name, and a non-empty secret_name. Qualifier and secret_key may both be
    empty (their meaning when empty is provider-defined). This is a
    structural check only; it does not verify that the provider is
    registered or that the secret exists.
    """
    if not isinstance(value, str):
        return False
    parts = value.split(':')
    if len(parts) != SRI_PARTS:
        return False
    provider, qualifier, secret_name, _secret_key = parts
    return (
        bool(_PROVIDER_RE.match(provider))
        and bool(_QUALIFIER_RE.match(qualifier))
        and bool(secret_name)
    )


def parse_sri(value: str) -> SecretProperties:
    """Parse an SRI string into :class:`SecretProperties`.

    Raises:
        SRIParseError: If the string is malformed. The message never includes
            the full input to avoid leaking values that only look like SRIs.
    """
    parts = value.split(':')
    if len(parts) != SRI_PARTS:
        raise SRIParseError(f'Malformed SRI with {len(parts)} part(s). {_FORMAT_HINT}')

    provider, qualifier, secret_name, secret_key = parts
    if not _PROVIDER_RE.match(provider):
        raise SRIParseError(
            f'Invalid SRI provider {provider!r}: must be a non-empty lowercase name. {_FORMAT_HINT}'
        )
    if not _QUALIFIER_RE.match(qualifier):
        raise SRIParseError(
            f'Invalid SRI qualifier {qualifier!r}: only letters, digits, ".", "_" and "-" '
            f'are allowed. {_FORMAT_HINT}'
        )
    if not secret_name:
        raise SRIParseError(f'SRI secret_name must be non-empty. {_FORMAT_HINT}')

    return SecretProperties(
        provider=provider,
        qualifier=qualifier or None,
        secret_name=secret_name,
        secret_key=secret_key or None,
    )
