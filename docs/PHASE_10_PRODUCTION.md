# QStock Phase 10 — Production Readiness

Phase 10 establishes the repository and deployment contract for a production Docker deployment. It does not claim that a public VPS, domain, DNS, TLS certificate, or cloud account has been provisioned; those require deployment credentials and infrastructure outside the repository.

## 10.1 Production architecture

```text
Internet
   |
   v
TLS / edge proxy
   |
   v
React + Nginx :80
   |
   v
FastAPI / Uvicorn
   |
   +---- PostgreSQL
   |
   +---- OpenAI or Ollama
```

Only the frontend is exposed at the edge in `docker-compose.production.yml`. PostgreSQL and the backend remain on internal Docker networking.

## 10.2 Environment and secrets

Use a deployment-platform secret store or an untracked `.env`. Never commit real credentials. The committed `.env.example` contains placeholders only.

Required production values include:

- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `DATABASE_URL`
- `SECRET_KEY`
- `BACKEND_CORS_ORIGINS`
- `INITIAL_ADMIN_EMAIL`
- `INITIAL_ADMIN_PASSWORD`

Set `DEBUG=false` and `ENVIRONMENT=production`.

## 10.3 Docker deployment

Validate configuration before deployment:

```bash
docker compose -f docker-compose.production.yml config
```

Build and start:

```bash
docker compose -f docker-compose.production.yml up -d --build
```

Verify:

```bash
docker compose -f docker-compose.production.yml ps
curl -f http://localhost/api/health
```

The successful health response must report database connectivity before traffic is accepted.

## 10.4 PostgreSQL backup

Run the repository backup script from a host with Docker access:

```bash
POSTGRES_USER=qr_admin POSTGRES_DB=qr_inventory ./scripts/backup-postgres.sh
```

The script creates compressed logical dumps and removes files older than `BACKUP_RETENTION_DAYS` (14 by default). Backups must be copied to storage independent from the database host for real disaster recovery.

A backup is not considered production-ready until a restore has been tested against an isolated PostgreSQL instance.

## 10.5 Releases

Production images are published to GitHub Container Registry when a semantic version tag such as `v1.0.0` is pushed. The workflow is `.github/workflows/release.yml`.

Recommended release sequence:

1. Merge tested changes.
2. Create and push a semantic version tag.
3. Confirm the GitHub Actions release succeeds.
4. Deploy the immutable version tag rather than relying on `latest`.
5. Run health and smoke tests.
6. Record the deployed version.

## 10.6 Rollback

Keep the previous known-good image tag available. If health, error rate, latency, cost, or AI evaluation regresses, redeploy that exact version and investigate the failed release separately.

Never roll back by deleting database data. Database changes must be backward-compatible with the application version being deployed.

## 10.7 Security baseline

- Backend and PostgreSQL are not directly published in the production compose file.
- Containers use `no-new-privileges`.
- Backend runs as a non-root user in its Docker image.
- Secrets are supplied through the environment/deployment platform.
- Production CORS is explicit.
- PostgreSQL data and uploads use persistent volumes.
- The application health check verifies database connectivity.

TLS termination should be provided by the selected production edge proxy/load balancer. Do not expose plain HTTP directly to the public Internet without an HTTPS layer.

## 10.8 Database migrations

The current application contains SQLAlchemy initialization and has Alembic installed, but a reviewed, versioned migration history is still required before a schema-changing production release. Do not treat `Base.metadata.create_all()` as a substitute for controlled migrations.

Before the first schema-changing production release:

1. Establish an Alembic migration baseline from the real schema.
2. Review the generated SQL.
3. Test upgrade and downgrade behavior on a disposable database.
4. Add the migration step to the deployment pipeline.
5. Take and verify a backup before applying migrations.

## 10.9 Launch gate

A production launch is accepted only when all of the following are true:

- CI is green.
- Production compose validates.
- Images build successfully.
- Secrets are externalized.
- HTTPS is configured.
- Database backup and restore are tested.
- Health and smoke tests pass.
- A versioned release is recorded.
- Monitoring and alerting are active.
- A rollback image is available.
