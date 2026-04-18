# Overview

## Business role

`lotus-advise` owns advisor-led proposal simulation and lifecycle workflows. It is the service that
turns advisory intent into governed simulation, persisted proposal workflow state, and execution
readiness posture.

## Ownership boundaries

This repo owns:

1. advisory proposal simulation orchestration
2. proposal lifecycle persistence and workflow history
3. approvals, consent, and execution-readiness semantics
4. backend-owned decision summary and proposal alternatives

This repo does not own:

1. management-only workflows, which belong to `lotus-manage`
2. canonical portfolio state and simulation authority, which belong to `lotus-core`
3. risk methodology authority, which belongs to `lotus-risk`

## Current posture

- advisory-only scope after the `lotus-manage` split
- explicit runtime smoke and production-profile guardrail validation in CI
- stateful upstream posture governed under RFC-0082
- persisted proposal evidence surfaces already matter for canonical and degraded runtime proof
