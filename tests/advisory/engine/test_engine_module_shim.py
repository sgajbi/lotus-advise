import src.core.advisory.engine as advisory_shim
import src.core.advisory_engine as advisory_engine


def test_advisory_engine_shim_exports_expected_entrypoints():
    assert advisory_shim.run_proposal_simulation is advisory_engine.run_proposal_simulation
    assert advisory_shim.build_reconciliation is advisory_engine.build_reconciliation
    assert advisory_shim.derive_status_from_rules is advisory_engine.derive_status_from_rules
