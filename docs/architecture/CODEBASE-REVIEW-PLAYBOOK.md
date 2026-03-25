# Lotus Advise Codebase Review Playbook

## Review Units

- Product surface and business fit
- Service boundaries and ecosystem integration
- API contract and workflow model
- Persistence, audit, and supportability
- Codebase hygiene and stale code

## Status Model

- `Planned`: not reviewed yet
- `Reviewed`: inspected with evidence captured
- `Hardened`: improved, but follow-up remains
- `Refactor Needed`: material gap confirmed
- `Signed Off`: reviewed with sufficient evidence and no material open risk in scope

## Evidence Required

- File references to source, docs, or tests
- Concrete finding class
- User or operator consequence
- Follow-up action with clear ownership seam

## Sign-Off Standard

A scope is only `Signed Off` when:

- the current implementation matches the intended responsibility,
- key risks are either fixed or explicitly deferred,
- integration boundaries are clear,
- residual gaps are listed in the ledger.
