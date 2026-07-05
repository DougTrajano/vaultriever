# Vaultriever

**Retrieve secrets in an ARN-like way from different vaults seamlessly** — compatible with
[pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/), with no custom
field types. Just `str` fields plus a reusable mixin.

Vaultriever lets you address a secret with a single, portable string — a **Secret Resource
Identifier (SRI)** — and resolve it transparently from the vault it lives in:

```
provider:qualifier:secret_name:secret_key
```

```python
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings
from vaultriever import SecretSRIMixin


class OpenAISettings(SecretSRIMixin, BaseSettings):
    openai_api_key: str | SecretStr = Field(
        default='aws:us-east-1:my-secret:OPENAI_API_KEY',
    )


settings = OpenAISettings()
settings.openai_api_key                     # SecretStr('**********') — masked
settings.openai_api_key.get_secret_value()  # the resolved secret
```

## Why Vaultriever?

- **One identifier, many vaults.** The same 4-part SRI addresses AWS Secrets Manager, Databricks,
  Azure Key Vault, GCP Secret Manager, and any [custom provider](custom-providers.md) you register —
  swap the `provider` segment, keep everything else.
- **Drop-in with pydantic-settings.** Add the [`SecretSRIMixin`](pydantic-settings.md) to a
  `BaseSettings` model and SRI-shaped values are resolved and wrapped in `SecretStr` automatically.
  Everything else — literals, URLs, non-string values — passes through untouched.
- **Exports values by default.** Validated values are written to `os.environ` under the field
  name by default; see the [opt out instructions](security.md#environment-export-writes-plaintext)
  if you want to disable that behavior.
- **Secrets stay masked.** Resolved values are wrapped in `SecretStr`, so they never leak through
  `repr()` or logs.
- **Lazy dependencies.** Provider SDKs (`boto3`, `databricks-sdk`) are imported only on first use,
  so you install only the extras you actually need.

## What it does

1. **Parse** SRI strings like `aws:us-east-1:my-secret:API_KEY`.
2. **Dispatch** the lookup to the registered provider for that scheme.
3. **Resolve** the secret transparently inside settings models via `SecretSRIMixin`, or on demand
   with the standalone [`resolve_secret`](api/resolver.md) function.

## Next steps

<div class="grid cards" markdown>

- :material-download:{ .lg .middle } **[Installation](installation.md)** — install Vaultriever and the provider
  extras you need.
- :material-rocket-launch:{ .lg .middle } **[Quick Start](quick-start.md)** — resolve your first secret in a few
  lines.
- :material-key-chain:{ .lg .middle } **[Secret Resource Identifiers](sri.md)** — learn the SRI format and its
  rules.
- :material-shield-lock:{ .lg .middle } **[Security](security.md)** — how secrets are handled and what to watch
  for.

</div>

## License

Vaultriever is released under the [MIT License](https://github.com/DougTrajano/vaultriever/blob/main/LICENSE).
