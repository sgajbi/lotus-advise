# Lotus Advise Security

This document records the current security hardening baseline for Lotus Advise.

## Current Baseline

- Dependency health and security audit are repo-native gates.
- API error-boundary hardening reduces the risk of leaking sensitive lower-layer details.
- Advisory-copilot structured payload tests reject raw AI payload and sensitive unredacted inputs.
- `pyproject.toml` now includes report-only Bandit configuration for future calibration.

## Current Gaps

- Bandit is configured but not installed/enforced in the current CI lane.
- Full authentication, authorization, CORS, header, and API abuse-protection inventories need
  separate implementation-backed review slices.
- Security findings must remain evidence-based and must not imply legal, regulatory, or bank
  certification signoff.

## Next Steps

- Add Bandit as report-only once the dependency is introduced.
- Baseline findings and suppress only governed false positives.
- Move to fail-on-new-regression before enforcing absolute security thresholds.
