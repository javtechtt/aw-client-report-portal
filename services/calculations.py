"""SACS and TCC calculations. Pure functions, no DB access.

All monetary inputs and outputs are decimal.Decimal. Floats are forbidden in
this codebase (drift on rounding produces incorrect financial reports).

Phase 4 implements the real math so that QuarterlyReport totals are accurate
the moment a snapshot is created. The full calculation-review UI lands in
Phase 5; this module is its math kernel.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable, Optional


@dataclass
class SacsResult:
    total_inflow: Decimal
    total_outflow: Decimal
    excess_transfer: Decimal
    private_reserve_target: Decimal
    floor_amount: Decimal


@dataclass
class TccResult:
    client_1_retirement_total: Decimal
    client_2_retirement_total: Decimal
    non_retirement_total: Decimal
    trust_total: Decimal
    grand_total: Decimal
    liabilities_total: Decimal


# -- helpers ----------------------------------------------------------------

_ZERO = Decimal("0")


def _decimal(value) -> Decimal:
    """Coerce anything to Decimal without going through float. None -> 0."""
    if value is None:
        return _ZERO
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


# -- public API -------------------------------------------------------------

def compute_age(dob: date, today: Optional[date] = None) -> int:
    """Years from dob to today (or `today` if explicitly provided)."""
    today = today or date.today()
    years = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        years -= 1
    return years


def compute_sacs(sacs_static) -> SacsResult:
    """Compute SACS values from a client's SacsStatic record.

    Rules (PRD glossary + §2b):
      total_inflow         = client_1_salary + (client_2_salary or 0)
      excess_transfer      = total_inflow - monthly_outflow_budget
      private_reserve_target is the user-stored value (Phase 2 form);
        the 6 * outflow + deductibles formula is the auto-suggested default
        but the user owns the final number per Rebecca's transcript.
      floor_amount         = sacs_static.floor_amount (defaults to $1,000)
    """
    c1 = _decimal(sacs_static.client_1_monthly_salary) if sacs_static else _ZERO
    c2 = _decimal(getattr(sacs_static, "client_2_monthly_salary", None)) if sacs_static else _ZERO
    inflow = c1 + c2

    outflow = _decimal(sacs_static.monthly_outflow_budget) if sacs_static else _ZERO
    excess = inflow - outflow

    prt = _decimal(sacs_static.private_reserve_target) if sacs_static else _ZERO
    floor = _decimal(sacs_static.floor_amount) if sacs_static else Decimal("1000")

    return SacsResult(
        total_inflow=inflow,
        total_outflow=outflow,
        excess_transfer=excess,
        private_reserve_target=prt,
        floor_amount=floor,
    )


def compute_report_totals(report) -> dict:
    """Recompute every field on a QuarterlyReport from its immutable snapshot
    balances (QuarterlyReportBalance rows) plus the client's current
    SacsStatic record.

    Pure: does NOT write to the database. The caller is responsible for
    applying the returned dict onto the report instance and committing.

    SACS values use the client's current SacsStatic (V1 does not snapshot
    SACS static fields per quarter; see Phase 5 limitations).
    TCC values use the snapshot's balance_at_report — this is what makes
    historical reports stable even if the master Account row is later edited.
    """
    sacs = compute_sacs(report.client.sacs_static)

    entries = [
        {
            "owner": b.account.owner,
            "category": b.account.category,
            "balance": b.balance_at_report,
        }
        for b in report.balances
        if b.account is not None
    ]
    tcc = compute_tcc(entries)

    return {
        "total_inflow":             sacs.total_inflow,
        "total_outflow":            sacs.total_outflow,
        "excess_transfer":          sacs.excess_transfer,
        "private_reserve_target":   sacs.private_reserve_target,
        "client_1_retirement_total": tcc.client_1_retirement_total,
        "client_2_retirement_total": tcc.client_2_retirement_total,
        "non_retirement_total":     tcc.non_retirement_total,
        "trust_total":              tcc.trust_total,
        "grand_total":              tcc.grand_total,
        "liabilities_total":        tcc.liabilities_total,
    }


def compute_tcc(entries: Iterable[dict]) -> TccResult:
    """Compute TCC totals from a list of (owner, category, balance) entries.

    `entries` is a generic shape so this function can run on:
      - master Account records (Phase 3 totals view)
      - submitted form values (Phase 4 quarterly entry)
      - historical QuarterlyReportBalance records (Phase 8)

    Each entry must expose `owner`, `category`, and `balance`
    (attribute or dict key). Liability balances are stored positive and
    reported separately per PRD §2b — they are NEVER subtracted from
    grand_total.
    """
    def _get(entry, key):
        if isinstance(entry, dict):
            return entry.get(key)
        return getattr(entry, key, None)

    def _sum(predicate):
        total = _ZERO
        for e in entries:
            if predicate(e):
                total += _decimal(_get(e, "balance"))
        return total

    c1_ret = _sum(lambda e: _get(e, "owner") == "client_1" and _get(e, "category") == "retirement")
    c2_ret = _sum(lambda e: _get(e, "owner") == "client_2" and _get(e, "category") == "retirement")
    non_ret = _sum(lambda e: _get(e, "category") == "non_retirement")
    trust = _sum(lambda e: _get(e, "category") == "trust")
    liabilities = _sum(lambda e: _get(e, "category") == "liability")

    return TccResult(
        client_1_retirement_total=c1_ret,
        client_2_retirement_total=c2_ret,
        non_retirement_total=non_ret,
        trust_total=trust,
        grand_total=c1_ret + c2_ret + non_ret + trust,
        liabilities_total=liabilities,
    )
