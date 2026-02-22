# Git Workflow With Protected `main`

This repo uses branch protection on `main`.

What this means:
- Do work on a feature branch.
- Open a PR to `main`.
- Merge only after CI passes.
- Do not push directly to `main`.

## Daily Flow (Step-by-Step)

### 1. Sync local `main`

```bash
git checkout main
git pull origin main
```

### 2. Create a branch

Use a short, clear branch name.

```bash
git checkout -b feat/<short-change-name>
```

Examples:
- `feat/add-risk-metric-endpoint`
- `fix/nightly-preflight-endpoint`

### 3. Make changes and run local checks

```bash
make check
```

If your change is broader:

```bash
make check-all
```

### 4. Commit

```bash
git add .
git commit -m "type: short summary"
```

Examples:
- `fix: handle empty policy pack catalog`
- `ci: tighten nightly preflight retries`

### 5. Push branch

```bash
git push -u origin feat/<short-change-name>
```

### 6. Open PR

```bash
gh pr create --fill --base main --head feat/<short-change-name>
```

If you want to edit title/body:

```bash
gh pr create --base main --head feat/<short-change-name>
```

### 7. Watch CI checks

```bash
gh pr checks <PR_NUMBER> --watch
```

### 8. Merge after green CI

```bash
gh pr merge <PR_NUMBER> --squash --delete-branch
```

Auto-merge is enabled via GitHub Action after successful CI.
If CI is green, PR can merge automatically.

### 9. Sync local after merge

```bash
git checkout main
git pull origin main
```

## If You Try to Push to `main` Directly

Protected branch rules will reject direct push.
Use branch + PR flow above.

## Dependabot PRs (Current Setup)

Dependabot opens dependency-update PRs.
Dependabot PRs follow the same auto-merge behavior after successful CI.

Useful commands:

```bash
gh pr list --author app/dependabot
gh pr checks <PR_NUMBER>
```

Manual merge (if needed):

```bash
gh pr merge <PR_NUMBER> --squash --delete-branch
```
