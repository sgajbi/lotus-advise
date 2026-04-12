# RFC-0022 Slice 6 Evidence: Persistence, Workspace, Artifact, and Replay Continuity

- RFC: `docs/rfcs/RFC-0022-proposal-alternatives-and-portfolio-construction-workbench.md`
- Slice: 6
- Date: 2026-04-13
- Status: Completed

## Scope

This slice closes the continuity gap for proposal alternatives after initial generation and ranking.

The focus is not candidate construction itself. The focus is preserving already-generated
alternatives and selected-alternative semantics across:

1. persisted proposal versions,
2. workspace save and resume flows,
3. workspace-to-lifecycle handoff,
4. proposal artifacts,
5. replay evidence and async replay surfaces.

## Delivered

### 1. Workspace draft state now preserves alternatives requests

`WorkspaceDraftState` now stores `alternatives_request`.

That matters because before this slice, workspace reconstruction preserved:

1. options,
2. reference model,
3. trade drafts,
4. cash-flow drafts,

but silently dropped proposal alternatives intent and any persisted `selected_alternative_id`.

That was a real continuity bug for RFC-0022.

### 2. Workspace reevaluation and handoff now retain selected alternatives

`src/api/services/workspace_service.py` now round-trips `alternatives_request` through:

1. workspace creation,
2. evaluation,
3. save,
4. resume,
5. handoff into proposal lifecycle.

This means selected-alternative intent is no longer lost when a workspace is persisted or handed
off into immutable proposal versions.

### 3. Selection-mode alternatives evaluation is now supported

`build_proposal_alternatives` now chooses normalization mode based on whether
`selected_alternative_id` is present.

This is the minimal truthful behavior needed for lifecycle and workspace selection writes:

1. first-time generation still rejects selection ids,
2. persisted and handoff flows can preserve a selected alternative deterministically.

### 4. Artifact surfaces now expose proposal alternatives explicitly

`ProposalArtifact` now carries `proposal_alternatives`.

This is important because Slice 6 requires alternatives to be present on artifact-facing evidence
surfaces, not only hidden inside raw engine outputs.

### 5. Replay evidence now surfaces proposal alternatives explicitly

Replay responses now include `proposal_alternatives` in:

1. workspace saved-version replay evidence,
2. proposal version replay evidence,
3. async replay evidence through the proposal replay projection.

That makes alternatives continuity auditable without requiring consumers to reverse-engineer nested
raw simulation payloads.

## Tests Added Or Tightened

Updated or added:

1. `tests/unit/advisory/engine/test_engine_proposal_artifact.py`
2. `tests/unit/advisory/engine/test_engine_proposal_workflow_service.py`
3. `tests/unit/advisory/api/test_api_workspace.py`
4. `tests/unit/advisory/api/test_api_advisory_proposal_lifecycle.py`

The slice now proves:

1. artifacts preserve proposal alternatives,
2. persisted proposal versions preserve selected alternatives,
3. workspace save and resume preserve selected alternatives,
4. workspace handoff preserves selected alternatives into proposal result and artifact,
5. workspace replay evidence surfaces proposal alternatives,
6. proposal and async replay evidence surface proposal alternatives consistently.

## Review Notes

The most important tightening in this slice was identifying that alternatives continuity was not a
proposal-repository problem first. It was a workspace reconstruction problem.

Proposal versions were already persisting the full proposal result.

The real loss of truth happened earlier because workspace draft reconstruction omitted
`alternatives_request`, which meant:

1. reevaluation silently lost alternatives intent,
2. save and resume could not preserve selection semantics,
3. handoff could not truthfully claim continuity.

That gap is now closed at the right boundary.

## Remaining For Later Slices

Still intentionally deferred:

1. live-stack alternatives validation and latency evidence,
2. final documentation, context, and branch-hygiene closure slice,
3. any future dedicated persisted alternatives read endpoint, if still needed after UI integration.
