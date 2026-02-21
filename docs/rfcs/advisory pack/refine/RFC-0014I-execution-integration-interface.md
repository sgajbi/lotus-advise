# RFC-0014I: Execution Integration Interface (OMS / Broker) + Trade Ticket & Acknowledgement Lifecycle

| Metadata | Details |
| --- | --- |
| **Status** | DRAFT |
| **Created** | 2026-02-18 |
| **Target Release** | MVP-14I |
| **Depends On** | RFC-0014E (Proposal Artifact) |
| **Strongly Recommended** | RFC-0014F (GateDecision), RFC-0014G (Persistence) |
| **Doc Location** | `docs/rfcs/advisory pack/refine/RFC-0014I-execution-integration-interface.md` |
| **Backward Compatibility** | Not required |

---

## 0. Executive Summary

RFC-0014I defines how an approved advisory proposal becomes **executed orders** by integrating with an OMS/broker layer.

It introduces:
- a canonical **Execution Request** API
- deterministic conversion from intents → **trade tickets**
- **dependency-aware** execution ordering (FX before BUYs)
- idempotent submit + acknowledgement lifecycle
- status tracking model (submitted/accepted/partially-filled/filled/rejected/cancelled)

This RFC is intentionally integration-first and remains vendor-neutral.

---

## 1. Motivation / Problem Statement

A proposal engine is only valuable in production if it can:
- produce executable trade instructions,
- submit them safely (idempotent),
- receive acknowledgements and fills,
- update the lifecycle state with full auditability.

The proposal artifact already contains deterministic intent ordering and dependencies. RFC-0014I turns that into an execution pipeline.

---

## 2. Scope

### 2.1 In Scope
- Define an **Execution Integration Interface** (port) and baseline HTTP APIs.
- Create **trade tickets** from `ProposalArtifact.trades_and_funding`.
- Submit execution requests idempotently.
- Track execution lifecycle events (accept/reject/fill/cancel).
- Support dependency graph execution sequencing:
  - CASH_FLOW (if applicable) → SELL → FX → BUY

### 2.2 Out of Scope
- Real broker connectivity details (FIX, proprietary)
- Best execution / smart routing logic
- Settlement, allocations, confirmations beyond basic status
- Partial order slicing logic (can be later RFC)
- Multi-day execution and time-in-force complexity (later RFC)

---

## 3. Preconditions

This RFC assumes:
- Proposal has passed required gates (GateDecision indicates EXECUTION_READY or equivalent).
- Proposal version is immutable and persisted (strongly recommended) so execution refers to a stable artifact.

If persistence is not yet implemented:
- execution request must carry the complete artifact + evidence bundle (heavier but possible).

---

## 4. Core Concepts

### 4.1 Trade Ticket
A normalized instruction derived from intents that can be sent to OMS/broker.

Ticket types:
- `SECURITY_ORDER`
- `FX_SPOT_ORDER`
- (optional later) `CASH_TRANSFER`

### 4.2 Execution Request
A request to execute the tickets associated with a specific proposal/version.

### 4.3 Execution Lifecycle
A set of states and events representing order submission and fills.

---

## 5. API Design

All endpoints follow the `/rebalance/...` route family.

### 5.1 Create execution request
`POST /rebalance/executions`

Headers:
- `Idempotency-Key` required
- `X-Correlation-Id` optional

Body:
```json
{
  "proposal_id": "prop_123",
  "version_no": 2,
  "execution_policy": {
    "time_in_force": "DAY",
    "allow_partial_fills": true,
    "max_slippage_bps": "25",
    "dry_run": false
  },
  "actor": {
    "requested_by": "advisor_001",
    "channel": "ADVISOR_APP"
  }
}
````

Response:

```json
{
  "execution_id": "exec_20260218_abc",
  "proposal_id": "prop_123",
  "version_no": 2,
  "status": "SUBMITTED",
  "tickets": [ ... ],
  "lineage": { "request_hash": "sha256:..." }
}
```

### 5.2 Get execution

`GET /rebalance/executions/{execution_id}`

Returns:

* execution summary
* tickets + per-ticket status
* lifecycle events

### 5.3 List executions

`GET /rebalance/executions?proposal_id=&status=&from=&to=&limit=&cursor=`

### 5.4 Receive external updates (webhook / callback)

Two models:

**Option A (preferred):** webhook endpoint exposed by this service
`POST /rebalance/executions/{execution_id}/events`

Body:

```json
{
  "source": "OMS_X",
  "event_type": "ORDER_ACCEPTED|ORDER_REJECTED|PARTIAL_FILL|FILLED|CANCELLED",
  "external_order_id": "OMS12345",
  "ticket_id": "tkt_001",
  "occurred_at": "2026-02-18T10:00:00Z",
  "details": { "filled_qty": "5", "avg_price": "149.80" }
}
```

**Option B:** this service polls OMS (later)

---

## 6. Ticket Generation (Deterministic)

### 6.1 Ticket ordering

Tickets must preserve proposal dependency order:

1. SELL security orders
2. FX spot orders
3. BUY security orders

(If cash flows are part of the execution system, place them ahead.)

### 6.2 Ticket identity

Ticket IDs must be deterministic to support idempotency and audit:

* `ticket_id = "tkt_" + sha1(proposal_version_hash + intent_id)[:12]`

### 6.3 Ticket schema

#### 6.3.1 Security Order Ticket

```json
{
  "ticket_id": "tkt_...",
  "ticket_type": "SECURITY_ORDER",
  "intent_id": "oi_...",
  "instrument_id": "US_EQ_ETF",
  "side": "BUY",
  "quantity": "10",
  "currency": "USD",
  "order_type": "MARKET",
  "time_in_force": "DAY",
  "dependencies": ["tkt_fx_..."],
  "constraints": {
    "max_slippage_bps": "25"
  }
}
```

#### 6.3.2 FX Spot Ticket

```json
{
  "ticket_id": "tkt_fx_...",
  "ticket_type": "FX_SPOT_ORDER",
  "intent_id": "oi_fx_...",
  "pair": "USD/SGD",
  "buy_currency": "USD",
  "buy_amount": "1500.00",
  "sell_currency": "SGD",
  "sell_amount_estimated": "2025.00",
  "order_type": "MARKET",
  "time_in_force": "DAY",
  "dependencies": []
}
```

---

## 7. Execution State Machine

### 7.1 Execution (aggregate) states

* `CREATED`
* `SUBMITTED`
* `ACCEPTED` (all tickets accepted)
* `PARTIALLY_FILLED`
* `FILLED`
* `REJECTED` (any critical ticket rejected)
* `CANCELLED`

### 7.2 Ticket states

* `PENDING_SUBMIT`
* `SUBMITTED`
* `ACCEPTED`
* `REJECTED`
* `PARTIAL_FILL`
* `FILLED`
* `CANCELLED`

### 7.3 State transition rules

* Execution becomes `REJECTED` if:

  * FX ticket rejected and BUY depends on it (cannot proceed)
  * critical SELL rejected (policy configurable)
* Execution becomes `FILLED` only when all tickets reach terminal filled/cancelled states as permitted by policy.

---

## 8. Idempotency & Safety

### 8.1 Execution create idempotency

* Idempotency-Key + canonical request hash ensures retries do not create duplicate executions.
* If a create request repeats with same key but differs:

  * 409 Problem Details

### 8.2 Exactly-once submission semantics (best effort)

If persistence exists:

* store execution + tickets in a single transaction
* submit to OMS after commit
* track submission attempts in an outbox table (later enhancement)

For MVP:

* at least ensure ticket IDs are deterministic so OMS can deduplicate if supported.

---

## 9. Integration Port (Adapter Pattern)

Define a port interface:

* `ExecutionProvider.submit_tickets(execution_id, tickets) -> SubmitResult`
* `ExecutionProvider.cancel_ticket(ticket_id) -> CancelResult`
* `ExecutionProvider.fetch_status(external_order_id) -> Status`

Provide an initial adapter stub:

* `MockExecutionProvider` for tests/demo
* later adapters:

  * FIX adapter
  * REST OMS adapter
  * internal broker adapter

---

## 10. Persistence (Recommended)

Add tables:

* `executions`
* `execution_tickets`
* `execution_events`
* `execution_idempotency_keys`

Store:

* proposal_id/version_no
* tickets JSONB
* external_order_ids mapping
* events append-only

If RFC-0014G already introduced a shared idempotency table, reuse it with a type discriminator.

---

## 11. Observability

Metrics:

* executions_created_total{status=...}
* tickets_submitted_total{type=...}
* tickets_rejected_total{reason=...}
* execution_latency_ms{stage=submit|ack|fill}

Logs:

* correlation_id
* execution_id
* proposal_id/version_no
* ticket_id/external_order_id

---

## 12. Testing Plan

### 12.1 Unit tests

* ticket generation determinism
* dependency mapping correctness
* execution state machine transitions
* idempotency conflicts

### 12.2 Integration tests

* using MockExecutionProvider:

  * accept all tickets
  * reject FX ticket
  * partial fill then fill

### 12.3 Golden tests

Not required for execution pipeline beyond determinism of tickets, but can snapshot generated tickets for demo scenarios.

---

## 13. Acceptance Criteria (DoD)

* System can create an execution request for a proposal version.
* Tickets are generated deterministically and include dependencies.
* Execution submission is idempotent.
* Status events update ticket and execution states deterministically.
* Rejection handling respects dependency constraints (FX rejection blocks dependent buys).
* Tests cover happy path + rejection + partial fill.

---

## 14. Follow-ups

* Outbox pattern for resilient submission
* Allocation to accounts, settlement instructions
* Multi-day execution, slicing, time windows
* Real OMS/FIX integration adapters
