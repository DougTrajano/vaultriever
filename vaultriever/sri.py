"""Secret Resource Identifier (SRI) parsing and validation.

Canonical format::

    provider:region:secret_name:secret_key

Examples:
    - ``aws:us-east-1:my-secret:OPENAI_API_KEY``
    - ``databricks::my-secret-scope:OPENAI_API_KEY`` (empty region -> default
      profile/workspace)
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from vaultriever.exceptions import SRIParseError

SRI_PARTS = 4
_PROVIDER_RE = re.compile(r'^[a-z][a-z0-9_-]*$')
# Regions/profiles are identifier-like. Keeping this strict prevents strings
# such as 'postgresql://user:pass@host:5432/db' from being detected as SRIs.
_REGION_RE = re.compile(r'^[A-Za-z0-9._-]*$')

_FORMAT_HINT = "Expected 'provider:region:secret_name:secret_key'"


@dataclass(frozen=True)
class SecretProperties:
    """Parsed components of an SRI string."""

    provider: str
    region: str | None
    secret_name: str
    secret_key: str


def is_sri(value: str) -> bool:
    """Return True if ``value`` is structurally a valid SRI.

    The check requires exactly 4 colon-separated parts, a lowercase provider
    name, and non-empty secret_name/secret_key. Only the region may be empty.
    This is a structural check only; it does not verify that the provider is
    registered or that the secret exists.
    """
    if not isinstance(value, str):
        return False
    parts = value.split(':')
    if len(parts) != SRI_PARTS:
        return False
    provider, region, secret_name, secret_key = parts
    return (
        bool(_PROVIDER_RE.match(provider))
        and bool(_REGION_RE.match(region))
        and bool(secret_name)
        and bool(secret_key)
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

    provider, region, secret_name, secret_key = parts
    if not _PROVIDER_RE.match(provider):
        raise SRIParseError(
            f'Invalid SRI provider {provider!r}: must be a non-empty lowercase name. {_FORMAT_HINT}'
        )
    if not _REGION_RE.match(region):
        raise SRIParseError(
            f'Invalid SRI region {region!r}: only letters, digits, ".", "_" and "-" '
            f'are allowed. {_FORMAT_HINT}'
        )
    if not secret_name:
        raise SRIParseError(f'SRI secret_name must be non-empty. {_FORMAT_HINT}')
    if not secret_key:
        raise SRIParseError(f'SRI secret_key must be non-empty. {_FORMAT_HINT}')

    return SecretProperties(
        provider=provider,
        region=region or None,
        secret_name=secret_name,
        secret_key=secret_key,
    )
