# Quick Start

This guide takes you from an installed package to resolved secrets in a few minutes. It assumes you
have already [installed Vaultriever](installation.md) with the extra for your vault (for example,
`vaultriever[aws]`).

## 1. Store a secret in your vault

Vaultriever reads secrets that already exist in a supported vault. For AWS Secrets Manager, the
secret must be a **JSON object**, and each key inside it becomes addressable:

```json
{
  "OPENAI_API_KEY": "sk-...",
  "DATABASE_PASSWORD": "..."
}
```

Given a secret named `my-secret` in region `us-east-1`, the key `OPENAI_API_KEY` is addressed by
the SRI:

```
aws:us-east-1:my-secret:OPENAI_API_KEY
```

See [Secret Resource Identifiers](sri.md) for the full format.

## 2. Resolve inside a settings model (recommended)

The idiomatic way to use Vaultriever is through [`SecretSRIMixin`](pydantic-settings.md) on a
`pydantic-settings` model. SRI-shaped values are resolved automatically and wrapped in `SecretStr`:

```python
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings
from vaultriever import SecretSRIMixin


class AppSettings(SecretSRIMixin, BaseSettings):
    openai_api_key: str | SecretStr = Field(
        default='aws:us-east-1:my-secret:OPENAI_API_KEY',
        description='OpenAI API key; an SRI or a literal value.',
    )


settings = AppSettings()

settings.openai_api_key                     # SecretStr('**********') — masked in repr/logs
settings.openai_api_key.get_secret_value()  # 'sk-...' — the resolved secret
```

Typically the SRI comes from the environment rather than a hard-coded default:

```bash
export OPENAI_API_KEY='aws:us-east-1:my-secret:OPENAI_API_KEY'
```

```python
settings = AppSettings()  # reads OPENAI_API_KEY from the environment, then resolves it
```

!!! info "Literals pass through"
    A value that is not a valid SRI — or whose provider is not registered — is left exactly as
    given. You can mix real secrets and plain defaults in the same model without special-casing.

## 3. Resolve a secret directly

If you just need a value outside of a settings model, use the standalone helpers:

```python
from vaultriever import is_sri, resolve_secret

is_sri('aws:us-east-1:my-secret:API_KEY')          # True

resolve_secret('aws:us-east-1:my-secret:API_KEY')  # 'sk-...'
```

`resolve_secret` always returns a plain `str`. Wrap it in `SecretStr` yourself if you need masking.

## What's next?

- **[Secret Resource Identifiers](sri.md)** — the exact grammar and validation rules.
- **[Pydantic Settings Integration](pydantic-settings.md)** — masking, env export, and opt-outs.
- **[Providers](providers.md)** — AWS, Databricks, Azure, and GCP specifics (auth, caching, qualifiers).
- **[Custom Providers](custom-providers.md)** — plug in your own vault.
