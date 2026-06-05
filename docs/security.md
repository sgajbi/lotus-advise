# Lotus Advise Security

This document records the current security hardening baseline for Lotus Advise.

## Current Baseline

- Dependency health and security audit are repo-native gates.
- API error-boundary hardening reduces the risk of leaking sensitive lower-layer details.
- Advisory-copilot structured payload tests reject raw AI payload and sensitive unredacted inputs.
- Bandit high-severity findings are enforced through `make bandit-high-severity-gate`, which is
  called by `make security-audit`.
- Current Bandit inventory remains visible in the quality baseline: `0` high, `26` medium, and `1`
  low severity finding.

## Current Gaps

- Medium and low Bandit findings still need evidence-backed classification before broader
  fail-on-new-regression enforcement.
- Full authentication, authorization, CORS, header, and API abuse-protection inventories need
  separate implementation-backed review slices.
- Security findings must remain evidence-based and must not imply legal, regulatory, or bank
  certification signoff.

## Next Steps

- Classify the current medium and low Bandit findings and suppress only governed false positives.
- Move medium/low Bandit classes to fail-on-new-regression before enforcing absolute security
  thresholds.
