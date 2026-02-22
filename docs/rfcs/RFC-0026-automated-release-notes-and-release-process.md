# RFC-0026: Automated Release Notes and Lightweight Release Process

| Metadata | Details |
| --- | --- |
| **Status** | PROPOSED |
| **Created** | 2026-02-22 |
| **Depends On** | RFC-0025 |
| **Doc Location** | `docs/rfcs/RFC-0026-automated-release-notes-and-release-process.md` |

## 1. Executive Summary

Define a low-maintenance release process for a solo-maintained repository that uses:

- automated release note draft generation from merged PRs,
- a lightweight changelog policy,
- minimal manual review before publishing a release.

The objective is to improve traceability and communication without introducing process overhead.

## 2. Problem Statement

Current delivery flow is CI-first and branch-protected, but release communication is ad hoc.
As changes accumulate (feature work, dependency upgrades, CI policy changes), there is no
consistent release artifact that answers:

1. What changed?
2. Is there any migration/operational impact?
3. What should be verified after deployment?

For a solo developer with AI-assisted velocity, missing release structure increases context loss
and slows incident/debug response.

## 3. Goals and Non-Goals

### 3.1 Goals

- Generate release notes automatically from merged PRs.
- Keep human effort per release under 5 minutes.
- Standardize release content sections (Added/Changed/Fixed/Security/CI-DevEx/Migration).
- Support GitHub Free constraints (no paid tooling dependency).
- Preserve current CI and branch protection behavior.

### 3.2 Non-Goals

- Introduce mandatory semantic versioning automation in this RFC.
- Replace existing PR/CI workflows.
- Implement heavyweight release orchestration tools.
- Enforce complex label taxonomies at initial rollout.

## 4. Proposed Design

### 4.1 Release Cadence and Trigger

Recommended default cadence for this repository:

1. Monthly scheduled release, or
2. On-demand release when a meaningful change batch lands.

Release creation remains explicit (human-triggered), while note drafting is automated.

### 4.2 Release Notes Source

Use GitHub auto-generated release notes as the baseline source:

- Input: merged PR titles/authors and categorized labels (when present).
- Output: draft release notes in GitHub Releases UI/API.

Human review is limited to:

1. release title,
2. top summary sentence,
3. migration/operational warnings (if any).

### 4.3 Changelog Policy

Maintain `CHANGELOG.md` using Keep-a-Changelog style sections:

1. Added
2. Changed
3. Fixed
4. Security
5. CI/DevEx
6. Migration Notes

Policy:

- Update changelog only for user/operator-impacting changes.
- Skip pure internal/no-impact noise.
- One concise line per meaningful item.

### 4.4 Minimal Label Strategy

Labels are optional at first and should remain lightweight:

- `feature`
- `fix`
- `security`
- `ci`
- `breaking` (reserved, explicit)

If labels are missing, release notes still generate from PR titles.

### 4.5 Breaking Change and Migration Contract

If a release includes migration or operational impact, release notes must include:

1. what changed,
2. required action,
3. validation command(s),
4. rollback guidance pointer (if available).

No new API status vocabulary is introduced by this RFC.

## 5. Test Plan

Validation before rollout completion:

1. Create a dry-run draft release from recent merged PRs.
2. Confirm generated notes include key merged PRs and links.
3. Validate changelog update workflow in one real PR.
4. Publish one pilot release and verify discoverability for:
   - runtime changes,
   - CI/process changes,
   - dependency upgrades.

Success criteria:

- Release note draft generation works without manual curation from scratch.
- End-to-end publish process stays under 5 minutes.
- No missing high-impact changes in pilot release notes.

## 6. Rollout/Compatibility

Phased rollout:

1. Phase 1: adopt release note template + manual publish using GitHub generated notes.
2. Phase 2: add lightweight changelog discipline in PR flow.
3. Phase 3: optional automation for scheduled draft release creation.

Compatibility:

- Additive only.
- No API contract changes.
- No CI gate changes required for initial adoption.

## 7. Status and Reason Code Conventions

This RFC introduces no new API statuses or reason codes.

Release labels (if used) are repository workflow metadata only and do not affect runtime behavior.

## 8. Open Questions and Decision Record

Decisions to finalize during implementation:

1. Monthly vs on-demand release cadence as default.
2. Whether `CHANGELOG.md` is mandatory for every release or only major operational releases.
3. Whether to enforce label presence on PRs for cleaner categorization.
4. Whether to auto-create draft releases on schedule or keep release creation manual.

Recommended initial decisions for solo mode:

1. cadence: on-demand + monthly checkpoint,
2. changelog: required only for impactful changes,
3. labels: optional,
4. draft creation: manual trigger with automated notes.
