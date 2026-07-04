# Vaultriever

Vaultriever resolves Secret Resource Identifier strings inside `pydantic-settings` models.

## What it does

- Parse SRI strings like `aws:us-east-1:my-secret:API_KEY`.
- Dispatch secret lookups to registered providers.
- Resolve secrets transparently inside settings models via `SecretSRIMixin`.

See the repository README for installation, usage, and provider details.
