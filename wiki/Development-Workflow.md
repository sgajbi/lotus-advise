# Development Workflow

## Local Working Loop

On a fresh checkout, create and activate a virtualenv before `make install` — see
[Getting-Started](Getting-Started#before-the-first-command) for why and how. Then use the
repository-native commands:

- `make install`
- `make check`
- `make ci`
- `make ci-local`
- `make ci-local-docker`
- `make run`
- `make docker-up` / `make docker-down`

Bring the local runtime up with `make docker-up` rather than `docker compose up -d --build`.
The target exports the build arguments the compose file forwards, so `/version` on the running
service reports the commit it was built from, and a checkout with uncommitted changes is
stamped `<sha>-dirty` instead of claiming that commit. A plain compose build takes the
`unknown` argument defaults, so evidence gathered against it cannot be attributed to any
revision.

## Delivery Model

This repository follows the platform development workflow and CI strategy standard.

Required model:

1. branch from `main`
2. keep one branch per RFC or slice
3. use PR-first delivery
4. keep required checks green
5. finish with `local = remote = main`

## What To Verify During Advisory Changes

Changes to advisory behavior should usually re-check:

1. proposal simulation behavior
2. proposal decision-summary posture
3. proposal alternatives posture
4. lifecycle persistence and versioning behavior
5. upstream-core and upstream-risk dependency alignment
