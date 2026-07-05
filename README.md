# vaultriever

Retrieve secrets in an ARN-like way from different vaults seamlessly, compatible with [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) — no custom field types, just `str` fields plus a reusable mixin.

## Secret Resource Identifier (SRI)

Secrets are addressed with a 4-part string:

```
provider:qualifier:secret_name:secret_key
```

| Provider | Example | Notes |
| --- | --- | --- |
| AWS Secrets Manager | `aws:us-east-1:my-secret:OPENAI_API_KEY` | Secret must be a JSON object; `secret_key` selects a key. |
| Databricks | `databricks::my-secret-scope:OPENAI_API_KEY` | Empty qualifier → default workspace/profile; non-empty qualifier → CLI profile name. |
| Azure Key Vault | `azure:my-vault:my-secret:latest` | Single-value secret; `secret_key` is the version (`latest` or a version id). |
| GCP Secret Manager | `gcp:my-project:my-secret:latest` | Single-value secret; `secret_key` is the version (`latest` or a version number). |

## Installation

```bash
pip install vaultriever[aws]         # AWS Secrets Manager
pip install vaultriever[databricks]  # Databricks (not needed on a Databricks runtime)
pip install vaultriever[azure]       # Azure Key Vault
pip install vaultriever[gcp]         # GCP Secret Manager
```

## Usage

### With pydantic-settings

```python
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings
from vaultriever import SecretSRIMixin


class OpenAISettings(SecretSRIMixin, BaseSettings):
    openai_api_key: str | SecretStr = Field(
        default='aws:us-east-1:my-secret:OPENAI_API_KEY',
        description='OpenAI API key; SRI or literal.',
    )


settings = OpenAISettings()
settings.openai_api_key                     # SecretStr('**********') — masked
settings.openai_api_key.get_secret_value()  # the resolved secret
```

Behavior:

- `str` / `SecretStr` values that look like an SRI (and reference a registered provider) are resolved and wrapped in `SecretStr`, so they stay masked in `repr()` and logs.
- Everything else passes through unchanged — literals, URLs, non-string values.
- Validated values are also exported to `os.environ` under the field name for downstream usage by default. **This writes resolved secrets in plaintext to the process environment**; see the [opt out instructions](docs/security.md#environment-export-writes-plaintext) and disable it per model:

```python
from typing import ClassVar


class MySettings(SecretSRIMixin, BaseSettings):
    enable_env_export: ClassVar[bool] = False

    api_key: str | SecretStr
```

### Standalone

```python
from vaultriever import is_sri, resolve_secret

is_sri('aws:us-east-1:my-secret:API_KEY')          # True
resolve_secret('aws:us-east-1:my-secret:API_KEY')  # 'sk-...'
```

### Custom providers

```python
from vaultriever import SecretProviderRegistry
from vaultriever.sri import SecretProperties


class MyVaultProvider:
    name = 'myvault'

    def get_secret_value(self, props: SecretProperties) -> str:
        ...


SecretProviderRegistry.register(MyVaultProvider())
# Now 'myvault:qualifier:name:key' SRIs resolve through it.
```

## Providers

### AWS Secrets Manager

- Credentials come from the AWS SDK default chain (env vars, profile, IAM role).
- The region is required and taken from the SRI.
- Secret payloads are cached per `(secret_name, region)` for the process lifetime; call `AWSSecretProvider.clear_cache()` after a rotation.

### Databricks

- On a Databricks runtime, secrets are read via the native `dbutils`.
- Elsewhere, the [databricks-sdk](https://github.com/databricks/databricks-sdk-py) is used with default authentication, or with the CLI profile named by the SRI's qualifier component (`databricks:staging:my-scope:MY_KEY`).

### Azure Key Vault

- Credentials come from `DefaultAzureCredential` (env vars, managed identity, Azure CLI, etc.).
- The qualifier is the vault name; the provider builds the vault URL as `https://<vault_name>.vault.azure.net/`.
- Secret values are cached per `(vault_name, secret_name, version)` for the process lifetime; call `AzureSecretProvider.clear_cache()` after a rotation.

### GCP Secret Manager

- Credentials come from Application Default Credentials (ADC).
- The qualifier is the GCP project id; the provider builds the resource name `projects/<project_id>/secrets/<secret_name>/versions/<version>`.
- Secret values are cached per `(project_id, secret_name, version)` for the process lifetime; call `GCPSecretProvider.clear_cache()` after a rotation.

## Development

```bash
uv sync --all-extras --dev
uv run pytest
uv run ruff check .
uv run mypy
```

Releases are published to PyPI by pushing a `vX.Y.Z` tag.

## License

[MIT](LICENSE)
