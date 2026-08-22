# CI/CD Quality Gates

Every pull request targeting `main` runs backend checks, frontend build checks, and a Docker validation/build job.

## Gates

- Python compilation
- Ruff linting
- Backend pytest suite
- Frontend dependency installation and production build
- Docker Compose configuration validation
- Backend container build

The pipeline intentionally uses placeholder CI secrets only. Production secrets are never required by CI.

## AI regression gate

The backend pytest suite includes the versioned QStock AI evaluation/regression tests from Phase 2 and the Phase 3 safety tests. Changes to intent routing, SQL generation/guarding, prompts, or answer generation therefore fail CI when existing behavior regresses.

## Dependency maintenance

Dependabot checks Python, npm, Docker, and GitHub Actions dependencies weekly.
