# Installation

Vaultriever requires **Python 3.10+** and works with `pydantic>=2.0` and `pydantic-settings>=2.0`.

## Install the core package

=== "pip"

    ```bash
    pip install vaultriever
    ```

=== "uv"

    ```bash
    uv add vaultriever
    ```

The core package pulls in only `pydantic` and `pydantic-settings`. Each provider's SDK is an
optional extra, so you install only what you use.

## Provider extras

Vaultriever imports provider SDKs lazily — you only need the extra for the vaults you actually read
from.

| Extra | Installs | Use when |
| --- | --- | --- |
| `aws` | `boto3` | Reading from **AWS Secrets Manager**. |
| `databricks` | `databricks-sdk` | Reading from **Databricks** *outside* a Databricks runtime. |

=== "pip"

    ```bash
    pip install "vaultriever[aws]"          # AWS Secrets Manager
    pip install "vaultriever[databricks]"   # Databricks (off-runtime)
    pip install "vaultriever[aws,databricks]"
    ```

=== "uv"

    ```bash
    uv add "vaultriever[aws]"
    uv add "vaultriever[databricks]"
    uv add "vaultriever[aws,databricks]"
    ```

!!! tip "Running on a Databricks runtime"
    On a Databricks cluster, secrets are read through the native `dbutils`, so the `databricks`
    extra is **not** required. Install it only when resolving Databricks secrets from elsewhere
    (local, CI, another host). See [Providers](providers.md#databricks) for details.

## Verify the installation

```python
import vaultriever

print(vaultriever.is_sri('aws:us-east-1:my-secret:API_KEY'))  # True
```

## Next steps

Head to the [Quick Start](quick-start.md) to resolve your first secret.
