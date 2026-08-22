# Security Policy

## Supported versions

Only the default branch is considered actively maintained.

## Reporting a vulnerability

Please do not disclose security vulnerabilities in public issues. Contact the repository owner privately through GitHub so the issue can be investigated before public disclosure.

When reporting, include the affected component, reproduction steps, impact, and any relevant logs or screenshots. Never include live credentials, API keys, passwords, tokens, or personal data.

## Security expectations

- Secrets must be supplied through environment variables or a secret manager.
- Real `.env` files must never be committed.
- Production credentials must be rotated if exposure is suspected.
- The SQL execution path is intended to remain read-only and protected by application-level validation.
