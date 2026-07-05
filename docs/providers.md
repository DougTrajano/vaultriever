# Providers

A **provider** knows how to read a secret from one kind of vault. Providers are registered by name
in the [`SecretProviderRegistry`](api/providers.md#vaultriever.providers.base.SecretProviderRegistry),
and the `provider` segment of an [SRI](sri.md) selects which one resolves a given value.

Vaultriever ships four built-in providers, registered automatically at import time:

| Provider | SRI scheme | Extra | Status |
| --- | --- | --- | --- |
| AWS Secrets Manager | `aws` | `vaultriever[aws]` | ✅ Available |
| Databricks | `databricks` | `vaultriever[databricks]` | ✅ Available |
| Azure Key Vault | `azure` | `vaultriever[azure]` | ✅ Available |
| GCP Secret Manager | `gcp` | `vaultriever[gcp]` | ✅ Available |

Provider SDKs are imported **lazily**, on first use — so registration is safe even when the
matching extra is not installed. You only hit an import error if you actually resolve a secret for
a provider whose SDK is missing.

## AWS Secrets Manager

**SRI form:** `aws:<region>:<secret_name>:<json_key>`

```
aws:us-east-1:my-secret:OPENAI_API_KEY
```

- **JSON secrets only.** The secret's `SecretString` must be a **JSON object**; `secret_key`
  selects one of its keys. Binary secrets and non-object JSON raise
  [`SecretRetrievalError`](api/exceptions.md#vaultriever.exceptions.SecretRetrievalError).
- **Region is required** and taken from the SRI. An empty region raises `SecretRetrievalError`.
- **Credentials** come from the standard AWS SDK default chain — environment variables, shared
  config/credentials profile, or an IAM role.
- **Caching.** Secret payloads are cached per `(secret_name, region)` for the process lifetime, so
  repeated key lookups against the same secret make a single API call. After a rotation, clear it:

  ```python
  from vaultriever.providers import AWSSecretProvider

  AWSSecretProvider.clear_cache()
  ```

### Example

Given a secret `my-secret` in `us-east-1`:

```json
{ "OPENAI_API_KEY": "sk-...", "DB_PASSWORD": "..." }
```

```python
from vaultriever import resolve_secret

resolve_secret('aws:us-east-1:my-secret:OPENAI_API_KEY')  # 'sk-...'
resolve_secret('aws:us-east-1:my-secret:DB_PASSWORD')     # '...' (same cached payload)
```

## Databricks

**SRI form:** `databricks:<profile>:<scope>:<key>`

The `region` segment is interpreted as a **Databricks CLI profile name**, and `secret_name` is the
**secret scope**:

| SRI | Behavior |
| --- | --- |
| `databricks::my-scope:MY_KEY` | **Empty** profile → default workspace. Uses the native `dbutils` on a Databricks runtime, otherwise the SDK's default authentication. |
| `databricks:staging:my-scope:MY_KEY` | Reads via the `staging` Databricks CLI profile. |

- **On a Databricks runtime**, secrets are read through the native `dbutils` — the `databricks`
  extra is not required.
- **Off-runtime**, the [databricks-sdk](https://github.com/databricks/databricks-sdk-py) is used
  (install `vaultriever[databricks]`) with default authentication, or the CLI profile named by the
  SRI's region.
- A missing SDK or unusable context raises
  [`DatabricksConfigurationError`](api/exceptions.md#vaultriever.exceptions.DatabricksConfigurationError).

### Example

```python
from vaultriever import resolve_secret

# Default workspace (empty profile)
resolve_secret('databricks::prod-scope:OPENAI_API_KEY')

# Named CLI profile
resolve_secret('databricks:staging:prod-scope:OPENAI_API_KEY')
```

## Azure Key Vault

**SRI form:** `azure:<vault_name>:<secret_name>:<version>`

```
azure:my-vault:my-secret:latest
```

- **Single-value secrets.** Unlike AWS, Key Vault secrets hold one value; `secret_key` is
  the **version** to read — the literal `latest`, or a specific version id.
- **`region` is the vault name**, not an Azure region. The provider builds the vault URL as
  `https://<vault_name>.vault.azure.net/`.
- **Credentials** come from `DefaultAzureCredential` — environment variables, managed
  identity, Azure CLI, Visual Studio Code, etc.
- **Caching.** Secret values are cached per `(vault_name, secret_name, version)` for the
  process lifetime. After a rotation, clear it:

  ```python
  from vaultriever.providers import AzureSecretProvider

  AzureSecretProvider.clear_cache()
  ```

### Example

```python
from vaultriever import resolve_secret

resolve_secret('azure:my-vault:my-secret:latest')      # latest version
resolve_secret('azure:my-vault:my-secret:abc123...')   # a specific version id
```

## GCP Secret Manager

**SRI form:** `gcp:<project_id>:<secret_name>:<version>`

```
gcp:my-project:my-secret:latest
```

- **Single-value secrets.** As with Azure, `secret_key` is the **version** to read — the
  literal `latest`, or a specific version number.
- **`region` is the GCP project id.** The provider builds the resource name
  `projects/<project_id>/secrets/<secret_name>/versions/<version>`.
- **Credentials** come from Application Default Credentials (ADC) — a service account key,
  `gcloud auth application-default login`, or the ambient identity on GCE/GKE/Cloud Run.
- **Caching.** Secret values are cached per `(project_id, secret_name, version)` for the
  process lifetime. After a rotation, clear it:

  ```python
  from vaultriever.providers import GCPSecretProvider

  GCPSecretProvider.clear_cache()
  ```

### Example

```python
from vaultriever import resolve_secret

resolve_secret('gcp:my-project:my-secret:latest')  # latest version
resolve_secret('gcp:my-project:my-secret:3')        # a specific version number
```

## Inspecting the registry

The registry is queryable at runtime:

```python
from vaultriever import SecretProviderRegistry

SecretProviderRegistry.available_providers()      # ['aws', 'azure', 'databricks', 'gcp']
SecretProviderRegistry.is_registered('aws')       # True
SecretProviderRegistry.get('aws')                 # the AWSSecretProvider instance
```

To add your own vault, see [Custom Providers](custom-providers.md).

## API reference

See the [providers API reference](api/providers.md) for the provider interface and registry.
