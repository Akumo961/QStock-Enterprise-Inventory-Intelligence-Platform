# QStock Production Runbook

## Pre-deployment

1. Provide production secrets through the deployment platform; never commit them.
2. Set `DEBUG=false` and `ENVIRONMENT=production`.
3. Configure a production PostgreSQL database and backups.
4. Configure the selected LLM provider and explicit model/timeouts.
5. Run the CI pipeline and review the AI evaluation results.
6. Build and scan the production container image.
7. Confirm the production `.env` contains a valid `DATABASE_URL`, `SECRET_KEY`, and CORS allow-list.

## Database migrations

Database schema changes are managed by Alembic. The backend container runs `alembic upgrade head` before starting Uvicorn and will fail closed if a migration cannot be applied.

For a manual deployment, run from `backend/`:

```bash
alembic current
alembic upgrade head
alembic current
```

Never use `Base.metadata.create_all()` as the production schema deployment mechanism. The application only verifies database connectivity at startup.

For an existing database created before Alembic was introduced, verify that its schema matches the Phase 10 baseline before stamping it with the baseline revision. Do not blindly run a destructive downgrade against production.

## Health and readiness

Before accepting traffic, verify the API health endpoint, database connectivity, authentication, and AI provider connectivity. Do not treat a successful container start as proof that the full AI workflow is healthy.

## Backups and restore verification

Run `backend/scripts/backup_postgres.sh` on a schedule outside the application container. Keep backup files on storage independent of the database host and restrict their permissions.

A backup is not considered operationally validated until a restore has been tested on a separate PostgreSQL instance. The minimum restore drill is:

1. Provision an empty PostgreSQL instance.
2. Restore the newest backup into it.
3. Run `alembic current` and confirm the expected revision.
4. Start QStock against the restored database.
5. Verify `/health`, authentication, inventory reads, and a representative transaction flow.
6. Record the restore date, backup identifier, migration revision, and result.

## Monitoring

Track request volume, error rate, p50/p95 latency, LLM call count, token usage, estimated cost, template-hit rate, deterministic-answer rate, database latency, and provider failures. Never log prompts, SQL, credentials, or personal data in metrics.

## Rollback

If a deployment causes elevated errors, latency, cost, or AI evaluation regressions, stop rollout and redeploy the previous known-good image. Preserve the failing version identifier and CI results for investigation.

For schema changes, use an explicit forward migration or a tested rollback plan. Do not rely on container rollback alone when the database schema has already advanced.

## Incident response

For suspected credential exposure, revoke/rotate the credential immediately, investigate Git history and logs, and document the incident. For AI regressions, disable or roll back the affected model/configuration before changing multiple components at once.
