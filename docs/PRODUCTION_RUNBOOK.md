# QStock Production Runbook

## Pre-deployment

1. Provide production secrets through the deployment platform; never commit them.
2. Set `DEBUG=false` and `ENVIRONMENT=production`.
3. Configure a production PostgreSQL database and backups.
4. Configure the selected LLM provider and explicit model/timeouts.
5. Run the CI pipeline and review the AI evaluation results.
6. Build and scan the production container image.

## Health and readiness

Before accepting traffic, verify the API health endpoint, database connectivity, authentication, and AI provider connectivity. Do not treat a successful container start as proof that the full AI workflow is healthy.

## Monitoring

Track request volume, error rate, p50/p95 latency, LLM call count, token usage, estimated cost, template-hit rate, deterministic-answer rate, database latency, and provider failures. Never log prompts, SQL, credentials, or personal data in metrics.

## Rollback

If a deployment causes elevated errors, latency, cost, or AI evaluation regressions, stop rollout and redeploy the previous known-good image. Preserve the failing version identifier and CI results for investigation.

## Incident response

For suspected credential exposure, revoke/rotate the credential immediately, investigate Git history and logs, and document the incident. For AI regressions, disable or roll back the affected model/configuration before changing multiple components at once.
