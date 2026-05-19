"""Assembles the context dicts consumed by report-rendering templates.

Phase 5 implements the Calculation Review context. SACS / TCC visual-preview
contexts (Phases 6/7) still stubbed.

These functions are read-only — no database writes.
"""
from decimal import Decimal
from typing import Any, Dict

from models import QuarterlyReport


GROUP_META = [
    ("client_1_retirement", "Client 1 Retirement"),
    ("client_2_retirement", "Client 2 Retirement"),
    ("non_retirement",      "Non-Retirement"),
    ("trust",               "Trust"),
    ("liabilities",         "Liabilities"),
]


def group_report_balances(report: QuarterlyReport) -> dict:
    """Group a report's snapshot balances into the same 5 buckets the TCC
    layout consumes. The balance row stays attached to its master Account
    so the template can read owner / category / type for display.

    Snapshot rows whose master account has been deleted are skipped
    defensively (FK enforcement should prevent this, but treat it as a no-op
    rather than failing the page).
    """
    groups: dict[str, list] = {key: [] for key, _ in GROUP_META}
    for b in sorted(report.balances, key=lambda x: x.id):
        a = b.account
        if a is None:
            continue
        if a.category == "retirement" and a.owner == "client_1":
            groups["client_1_retirement"].append(b)
        elif a.category == "retirement" and a.owner == "client_2":
            groups["client_2_retirement"].append(b)
        elif a.category == "non_retirement":
            groups["non_retirement"].append(b)
        elif a.category == "trust":
            groups["trust"].append(b)
        elif a.category == "liability":
            groups["liabilities"].append(b)
    return groups


def group_totals(groups: dict) -> dict:
    out = {}
    for key, balances in groups.items():
        total = Decimal("0")
        for b in balances:
            if b.balance_at_report is not None:
                total += Decimal(b.balance_at_report)
        out[key] = total
    return out


def compute_warnings(report: QuarterlyReport, groups: dict) -> list[dict]:
    """Surface non-blocking conditions a planner should glance at before
    handing the report to a client. Each warning is one of three levels:

      error   — needs attention; the report is technically valid but the
                numbers are likely wrong if not addressed
      warning — caution; advise verification
      info    — neutral note; data is consistent but worth flagging
    """
    warnings: list[dict] = []

    stale_count = sum(1 for g in groups.values() for b in g if b.account and b.account.status == "stale")
    missing_count = sum(1 for g in groups.values() for b in g if b.account and b.account.status == "missing")

    if missing_count:
        warnings.append({
            "level": "error",
            "title": f"{missing_count} account{'' if missing_count == 1 else 's'} marked missing",
            "detail": "Balance data is flagged as missing — verify the value with the institution before sharing this report.",
        })

    if stale_count:
        warnings.append({
            "level": "warning",
            "title": f"{stale_count} account{'' if stale_count == 1 else 's'} marked stale",
            "detail": "Balance may not reflect the latest value; consider refreshing before the client meeting.",
        })

    if report.excess_transfer is not None and Decimal(report.excess_transfer) < 0:
        shortfall = abs(Decimal(report.excess_transfer))
        warnings.append({
            "level": "error",
            "title": "Outflow exceeds inflow",
            "detail": f"Excess transfer is negative (${shortfall:,.2f} shortfall). Review monthly outflow budget or salary inputs on the client profile.",
        })

    if not groups["trust"]:
        warnings.append({
            "level": "info",
            "title": "No trust accounts on file",
            "detail": "Trust total will display as $0 on the TCC report. Add a trust account if the household has one.",
        })

    if not groups["liabilities"]:
        warnings.append({
            "level": "info",
            "title": "No liabilities on file",
            "detail": "Liabilities section will display as $0 on the TCC report.",
        })

    return warnings


def build_review_context(report: QuarterlyReport) -> Dict[str, Any]:
    """Return everything the Calculation Review template (reports/show.html)
    needs to render — pure read of current DB state, no writes."""
    groups = group_report_balances(report)
    return {
        "report": report,
        "client": report.client,
        "groups": groups,
        "group_meta": GROUP_META,
        "group_totals": group_totals(groups),
        "warnings": compute_warnings(report, groups),
    }


# -- Phase 6 / 7 stubs (kept here so renderers can be wired progressively) --

def prepare_sacs_context(report: QuarterlyReport) -> Dict[str, Any]:
    """Build the context dict consumed by templates/reports/sacs.html.

    All monetary numbers come from the QuarterlyReport row (which Phase 5's
    calculation engine populated from snapshot balances) and from the
    client's SacsStatic record. Live Account balances are NEVER read here.

    Same template + context will be re-used by WeasyPrint in Phase 8 to
    produce the downloadable PDF, so the data shape must be stable.
    """
    client = report.client
    s = client.sacs_static

    salary_breakdown = None
    if s is not None:
        salary_breakdown = {
            "c1": s.client_1_monthly_salary,
            "c2": s.client_2_monthly_salary,  # may be None for single households
        }

    groups = group_report_balances(report)
    warnings = compute_warnings(report, groups)

    return {
        "report":                      report,
        "client":                      client,
        "report_date":                 report.report_date,
        "quarter_label":               report.quarter_label,
        "total_inflow":                report.total_inflow,
        "total_outflow":               report.total_outflow,
        "excess_transfer":             report.excess_transfer,
        "private_reserve_target":      report.private_reserve_target,
        "floor_amount":                s.floor_amount if s else Decimal("1000"),
        "insurance_deductibles_total": s.insurance_deductibles_total if s else Decimal("0"),
        "salary_breakdown":            salary_breakdown,
        "warnings":                    warnings,
    }


LAYOUT_CAPS = {
    "client_1_retirement": 6,
    "client_2_retirement": 6,
    "non_retirement":      8,
    "trust":               4,
    "liabilities":         6,
}


def _layout_warnings(groups: dict) -> list[dict]:
    """Surface non-breaking warnings when an account-count region exceeds its
    documented safe limit. The TCC template wraps overflowing rows rather
    than truncating, so the report stays correct — just larger."""
    notes = []
    pretty = {
        "client_1_retirement": "Client 1 retirement",
        "client_2_retirement": "Client 2 retirement",
        "non_retirement":      "Non-retirement",
        "trust":               "Trust",
        "liabilities":         "Liabilities",
    }
    for key, cap in LAYOUT_CAPS.items():
        n = len(groups[key])
        if n > cap:
            notes.append({
                "level":  "warning",
                "title":  f"{pretty[key]} section has {n} entries (safe cap is {cap})",
                "detail": "The TCC layout will wrap but may exceed one printed page.",
            })
    return notes


def prepare_tcc_context(report: QuarterlyReport) -> Dict[str, Any]:
    """Build the context dict consumed by templates/reports/tcc.html.

    All snapshot balances come from QuarterlyReportBalance — never live
    Account.balance. Account display metadata (type, owner, last-4) is
    still read from the master Account row that each snapshot points at
    (V1 trade-off documented in Phase 4).

    Same template + context shape will be re-used by WeasyPrint in
    Phase 8 to produce the downloadable PDF.
    """
    client = report.client
    persons = {p.role: p for p in client.persons}
    groups = group_report_balances(report)

    has_stale = any(
        b.account is not None and b.account.status in ("stale", "missing")
        for g in groups.values()
        for b in g
    )

    warnings = compute_warnings(report, groups) + _layout_warnings(groups)

    return {
        "report":      report,
        "client":      client,
        "client_1":    persons.get("client_1"),
        "client_2":    persons.get("client_2"),
        "groups":      groups,
        "has_stale":   has_stale,
        "warnings":    warnings,
    }
