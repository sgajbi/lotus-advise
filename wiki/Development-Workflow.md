# Development Workflow

## Daily loop

1. branch from `main`
2. keep advisory-only scope and boundaries explicit
3. run targeted proof first
4. run repo-native lane commands before pushing
5. update docs and repo context when advisory truth changes

## Common commands

```bash
make install
make run
make check
make ci
make ci-local
```

## Repo-specific expectations

- preserve advisory vs management boundaries
- keep proposal decision summary and proposal alternatives backend-owned
- preserve canonical upstream URL truth in README and Docker docs
- treat runtime smoke and production-profile guardrail checks as real contract behavior
