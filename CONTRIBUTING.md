# Contributing Guidelines

- **Branch Naming**: Use the format `feat/pr-XX-slug` (e.g., `feat/pr-01-scaffold`).
- **Commits**: Use [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `chore:`, `test:`, `docs:`).
- **PRs**: A PR template is required. Squash-merge into `main` after CI passes.
- **Multi-Tenancy**: All tenant-scoped tables must use Row-Level Security (RLS) filtering on `tenant_id = current_setting('app.current_tenant')::uuid`. See [Architecture](docs/ARCHITECTURE.md) for details.
- No direct pushes to main.
