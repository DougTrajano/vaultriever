# Secret Resource Identifiers

A **Secret Resource Identifier (SRI)** is a single, portable string that fully addresses one secret
value in one vault. It is the core abstraction in Vaultriever — the same shape works across every
provider.

## Format

```
provider:qualifier:secret_name:secret_key
```

An SRI is always **exactly four colon-separated parts**:

| Part | Required | Description |
| --- | --- | --- |
| `provider` | ✅ | The vault scheme, e.g. `aws`, `databricks`, `azure`, `gcp`. Must be a lowercase name. Selects which registered [provider](providers.md) resolves the secret. |
| `qualifier` | — | Provider-specific location or profile. May be **empty**. For AWS it is the region; for Databricks it is the CLI profile name; for Azure it is the vault name; for GCP it is the project id. |
| `secret_name` | ✅ | The secret's identifier within the vault (an AWS secret name, a Databricks scope, an Azure/GCP secret name, …). |
| `secret_key` | ✅ | The key selected from within the secret (a JSON key for AWS, a secret key for Databricks, a version for Azure/GCP). |

Only `qualifier` may be empty. `provider`, `secret_name`, and `secret_key` must all be non-empty.

## Examples

```
aws:us-east-1:my-secret:OPENAI_API_KEY
databricks::my-secret-scope:OPENAI_API_KEY
databricks:staging:my-secret-scope:MY_KEY
azure:my-vault:my-secret:latest
gcp:my-project:my-secret:latest
```

- `aws:us-east-1:my-secret:OPENAI_API_KEY` — the `OPENAI_API_KEY` key of the JSON secret `my-secret`
  in region `us-east-1`.
- `databricks::my-secret-scope:OPENAI_API_KEY` — an **empty** qualifier means the default Databricks
  workspace/profile.
- `databricks:staging:my-secret-scope:MY_KEY` — a non-empty qualifier names the Databricks CLI
  profile `staging`.
- `azure:my-vault:my-secret:latest` — the latest version of secret `my-secret` in Key Vault
  `my-vault`.
- `gcp:my-project:my-secret:latest` — the latest version of secret `my-secret` in GCP project
  `my-project`.

## Validation rules

Vaultriever validates the **structure** of an SRI, not the existence of the secret:

- Exactly `4` colon-separated parts.
- `provider` matches `^[a-z][a-z0-9_-]*$` — lowercase, starting with a letter.
- `qualifier` matches `^[A-Za-z0-9._-]*$` — letters, digits, `.`, `_`, `-`, or empty.
- `secret_name` and `secret_key` are non-empty.

The strict `qualifier` grammar is deliberate: it prevents colon-heavy strings such as
`postgresql://user:pass@host:5432/db` from being mistaken for an SRI.

## Checking and parsing SRIs

Use [`is_sri`](api/sri.md#vaultriever.sri.is_sri) for a structural check, and
[`parse_sri`](api/sri.md#vaultriever.sri.parse_sri) to split a string into its parts:

```python
from vaultriever import is_sri, parse_sri

is_sri('aws:us-east-1:my-secret:API_KEY')             # True
is_sri('postgresql://user:pass@host:5432/db')         # False

props = parse_sri('aws:us-east-1:my-secret:API_KEY')
props.provider      # 'aws'
props.qualifier     # 'us-east-1'
props.secret_name   # 'my-secret'
props.secret_key    # 'API_KEY'
```

An **empty qualifier** is normalized to `None` on the parsed
[`SecretProperties`](api/sri.md#vaultriever.sri.SecretProperties):

```python
parse_sri('databricks::my-scope:MY_KEY').qualifier  # None
```

`parse_sri` raises [`SRIParseError`](api/exceptions.md#vaultriever.exceptions.SRIParseError) for
malformed strings. To avoid leaking values that merely *look* like secrets, its error messages
never include the full input.

!!! note "Structural vs. resolvable"
    `is_sri` only tells you a string is *shaped* like an SRI. It does **not** check that the
    provider is registered or that the secret exists. When resolving inside
    [`SecretSRIMixin`](pydantic-settings.md), Vaultriever additionally requires the provider to be
    registered before treating a value as an SRI — so unknown-scheme strings pass through as plain
    literals.

## API reference

See the [SRI API reference](api/sri.md) for full signatures and docstrings.
