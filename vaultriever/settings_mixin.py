"""Pydantic-settings integration.

:class:`SecretSRIMixin` adds a wildcard ``mode='before'`` validator that
detects SRI strings in ``str``/``SecretStr`` fields and replaces them with the
resolved secret wrapped in ``SecretStr``.
"""

from __future__ import annotations

import json
import os
from typing import Any, ClassVar

from pydantic import SecretStr, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from vaultriever.logging import get_logger
from vaultriever.providers import SecretProviderRegistry
from vaultriever.resolver import resolve_secret
from vaultriever.sri import is_sri

logger = get_logger(__name__)


class SecretSRIMixin(BaseSettings):
    """Base/mixin for ``BaseSettings`` models that resolves SRI values.

    It extends ``BaseSettings`` (which keeps type checkers happy about
    ``model_config``), so both forms work::

        class MySettings(SecretSRIMixin):
            api_key: str | SecretStr = 'aws:us-east-1:my-secret:API_KEY'

        class MySettings(SecretSRIMixin, BaseSettings):
            api_key: str | SecretStr = 'aws:us-east-1:my-secret:API_KEY'

    Behavior:
    - ``str``/``SecretStr`` values that look like an SRI *and* reference a
      registered provider are resolved and returned as ``SecretStr``.
    - All other values pass through unchanged.
    - When ``enable_env_export`` is True (the default), validated values are
      also written to ``os.environ`` under the field name. Note that this
      writes resolved secrets in **plaintext** to the process environment;
      set ``enable_env_export: ClassVar[bool] = False`` on your subclass to
      opt out (the ``ClassVar`` annotation keeps pydantic from treating it as
      a field).
    """

    # Ensures SRI strings used as field defaults are also resolved.
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(validate_default=True)

    enable_env_export: ClassVar[bool] = True

    @field_validator('*', mode='before')
    @classmethod
    def resolve_sri(cls, value: Any, info: ValidationInfo) -> Any:
        if isinstance(value, SecretStr):
            raw = value.get_secret_value()
        elif isinstance(value, str):
            raw = value
        else:
            return value

        # Only treat the value as an SRI if its provider is registered, so
        # colon-heavy strings such as connection URLs pass through untouched.
        if is_sri(raw) and SecretProviderRegistry.is_registered(raw.split(':', 1)[0]):
            logger.debug('Resolving SRI for field %r', info.field_name)
            secret = SecretStr(resolve_secret(raw))
            cls._export_to_env(info.field_name, secret.get_secret_value())
            return secret

        cls._export_to_env(info.field_name, raw)
        return value

    @classmethod
    def _export_to_env(cls, field_name: str | None, value: Any) -> None:
        if not cls.enable_env_export or not field_name:
            return
        if isinstance(value, dict | list):
            os.environ[field_name] = json.dumps(value)
        else:
            os.environ[field_name] = str(value)
