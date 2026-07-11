# Lotus Advise Security

This document records the current security hardening baseline for Lotus Advise.

## Current Baseline

- Dependency health and security audit are repo-native gates.
- API error-boundary hardening reduces the risk of leaking sensitive lower-layer details.
- Advisory-copilot structured payload tests reject raw AI payload and sensitive unredacted inputs.
- Downstream `lotus-report` and `lotus-ai` requests require bounded trusted actor and tenant
  identity; missing or malformed values fail closed before HTTP submission.
- Downstream report requests require source-derived as-of date, reporting currency, and
  jurisdiction/booking-center metadata; missing or conflicting values fail closed before HTTP
  submission.
- Bandit security findings are enforced through `make bandit-severity-regression-gate`, which is
  called by `make security-audit` and has a compatibility alias at
  `make bandit-high-severity-gate`.
- Current Bandit inventory is governed by `quality/bandit_security_baseline.v1.json`: `0` high,
  `26` medium, and `0` low severity findings. High findings are never baselined; current medium/low
  entries require owner, rationale, expiry, linked remediation, and compensating controls.
- HTTP boundary controls are service-owned for trusted host validation, deny-by-default browser
  origin posture, approved security response headers, write-payload size limits, and enterprise
  audit/authorization denials. Production-like profiles must configure `HTTP_BOUNDARY_TRUSTED_HOSTS`
  when `ENTERPRISE_ENFORCE_RUNTIME_CONFIG=true`; wildcard trusted hosts or wildcard CORS origins
  are rejected in production-like environments.
- Browser CORS remains disabled unless `HTTP_BOUNDARY_ALLOWED_ORIGINS` names explicit allowed
  origins. Advise does not publish browser-origin support through OpenAPI unless the deployment
  config has approved origins.

## Current Gaps

- The current Bandit medium baseline remains non-certifying security debt. Issue #435 tracks
  reducing or retiring the constant-owned SQL-template entries before their `2026-12-31` expiry.
- Route-level authentication and authorization inventory remains a separate implementation-backed
  slice. Current HTTP boundary controls add host/origin/header/payload safeguards but do not replace
  trusted caller-context resolution for every public route.
- Route-specific throttling, back-pressure, and platform WAF/rate-limit policy remain owned by the
  ingress/gateway deployment contract unless a future Advise issue adds service-local quotas for a
  specific route family.
- Broader route-level authenticated caller-context resolution remains a separate authorization
  slice; this baseline covers downstream identity propagation for report and AI adapters.
- Security findings must remain evidence-based and must not imply legal, regulatory, or bank
  certification signoff.

## Next Steps

- Reduce the current medium Bandit baseline by replacing constant-owned SQL template false
  positives with Bandit-clean helpers where practical.
- Keep HTTP boundary tests in the API unit suite when adding new public route families, especially
  for validation-error, authorization-denial, and problem-details responses.
