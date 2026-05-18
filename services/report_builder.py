"""Assembles the context dict consumed by both browser preview and PDF render.

Phase 1 ships stubs that document the contract templates will read.
Real implementations land in Phase 5 (calculation review) and Phases 6-7
(SACS / TCC preview).
"""
from typing import Any, Dict


def build_sacs_context(report) -> Dict[str, Any]:
    """Phase 6: returns a context dict for the SACS template containing
    client, header_date, total_inflow, total_outflow, excess_transfer,
    private_reserve_target, floor_amount, and per-person salary breakdown.
    """
    raise NotImplementedError("build_sacs_context lands in Phase 6")


def build_tcc_context(report) -> Dict[str, Any]:
    """Phase 7: returns a context dict for the TCC template containing
    client, persons (with computed age), accounts grouped by (owner, category),
    grand_total, retirement totals per client, non_retirement_total,
    trust_total, liabilities_total, and a layout-validation result.

    Validates per-region bubble caps (see TCC layout strategy in the Phase 1
    plan): raises if any region exceeds its maximum so the renderer cannot
    produce an overlapping or broken layout.
    """
    raise NotImplementedError("build_tcc_context lands in Phase 7")
