"""SACS and TCC calculations. Pure functions, no DB access.

All monetary inputs and outputs are decimal.Decimal. Floats are forbidden in
this codebase (drift on rounding produces incorrect financial reports).
Real implementations land in Phase 5.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional


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


def compute_age(dob: date, today: Optional[date] = None) -> int:
    """Years from dob to today (or `today` if explicitly provided)."""
    today = today or date.today()
    years = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        years -= 1
    return years


def compute_sacs(*args, **kwargs) -> SacsResult:
    """Phase 5: compute SACS values from a client's SacsStatic record.

    Rules (PRD glossary + §2b):
      total_inflow         = client_1_salary + (client_2_salary or 0)
      excess_transfer      = total_inflow - monthly_outflow_budget
      private_reserve_target = 6 * monthly_outflow_budget + insurance_deductibles_total
      floor_amount         = $1,000 (constant)
    """
    raise NotImplementedError("compute_sacs lands in Phase 5")


def compute_tcc(*args, **kwargs) -> TccResult:
    """Phase 5: compute TCC totals from a client's accounts.

    Rules (PRD §2b — these are exact, per Rebecca's transcript):
      per-client retirement = sum(balance) where owner=client_X AND category='retirement'
      non_retirement_total  = sum(balance) where category='non_retirement'   (trust excluded)
      trust_total           = sum(balance) where category='trust'
      grand_total           = c1_ret + c2_ret + non_ret + trust
      liabilities_total     = sum(balance) where category='liability'
                              displayed separately, NEVER subtracted from grand_total
    """
    raise NotImplementedError("compute_tcc lands in Phase 5")
