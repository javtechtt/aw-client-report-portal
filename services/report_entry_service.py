"""Quarterly report entry domain service.

Loads the data needed for the entry form (current accounts + previous
report values), validates submitted balances, and creates an immutable
QuarterlyReport + QuarterlyReportBalance snapshot. After successful
submission, the master Account latest values (balance, cash_balance,
date_updated, status) are synced to the entered values so the next
quarterly entry starts from the most recent numbers.

The calculation math is delegated to services/calculations.py.
"""
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Mapping, Optional

from extensions import db
from models import (
    ACCOUNT_STATUSES,
    Client,
    QuarterlyReport,
    QuarterlyReportBalance,
)
from services import account_service, calculations

_ZERO = Decimal("0")


# -- context loading --------------------------------------------------------

def build_entry_context(client: Client) -> dict:
    """Returns everything the new-report form template needs."""
    groups = account_service.group_for_display(client)
    previous_report, previous_balances = _load_previous(client)

    return {
        "groups": groups,
        "previous_report": previous_report,
        "previous_balances": previous_balances,
        "previous_label": previous_report.quarter_label if previous_report else None,
        "default_form": _initial_form(client),
    }


def _load_previous(client: Client) -> tuple[Optional[QuarterlyReport], dict[int, QuarterlyReportBalance]]:
    """Returns (most_recent_report, {account_id: balance_record}).

    Empty dict if no prior report exists.
    """
    if not client.reports:
        return None, {}
    prev = client.reports[0]  # ordered report_date desc by relationship
    balances = {b.account_id: b for b in prev.balances}
    return prev, balances


def _initial_form(client: Client) -> dict:
    """Build the form dict that pre-fills the entry form on GET.

    Per-account balance defaults to the current master Account.balance
    so the operator can adjust rather than retype.
    """
    today = date.today().isoformat()
    form: dict[str, str] = {
        "report_date": today,
        "quarter_label": _suggest_quarter_label(),
    }
    for acct in client.accounts:
        form[f"account_{acct.id}_balance"] = _money_str(acct.balance)
        form[f"account_{acct.id}_cash_balance"] = _money_str(acct.cash_balance) if acct.cash_balance is not None else ""
        form[f"account_{acct.id}_date_updated"] = (
            acct.date_updated.isoformat() if acct.date_updated else today
        )
        form[f"account_{acct.id}_status"] = acct.status or "up_to_date"
    return form


def _suggest_quarter_label(today: Optional[date] = None) -> str:
    today = today or date.today()
    q = (today.month - 1) // 3 + 1
    return f"Q{q} {today.year}"


def _money_str(value) -> str:
    if value is None:
        return ""
    return f"{Decimal(value):.2f}"


# -- validation -------------------------------------------------------------

def validate(form: Mapping[str, str], client: Client) -> dict[str, str]:
    errors: dict[str, str] = {}
    today = date.today()

    err = _validate_date(form.get("report_date"), today, required=True)
    if err:
        errors["report_date"] = err

    if not (form.get("quarter_label") or "").strip():
        errors["quarter_label"] = "Required."

    if not client.sacs_static:
        errors["sacs_static"] = (
            "Client SACS static fields are missing — edit the client and add "
            "monthly outflow budget before creating a report."
        )

    for acct in client.accounts:
        prefix = f"account_{acct.id}"

        err = _validate_money(form.get(f"{prefix}_balance"), required=True)
        if err:
            errors[f"{prefix}_balance"] = err

        if (form.get(f"{prefix}_cash_balance") or "").strip():
            err = _validate_money(form.get(f"{prefix}_cash_balance"), required=False)
            if err:
                errors[f"{prefix}_cash_balance"] = err

        if (form.get(f"{prefix}_date_updated") or "").strip():
            err = _validate_date(form.get(f"{prefix}_date_updated"), today, required=False)
            if err:
                errors[f"{prefix}_date_updated"] = err

        status = (form.get(f"{prefix}_status") or "").strip()
        if status not in ACCOUNT_STATUSES:
            errors[f"{prefix}_status"] = "Required."

    return errors


def _validate_date(value, today: date, required: bool) -> Optional[str]:
    value = (value or "").strip()
    if not value:
        return "Required." if required else None
    try:
        d = date.fromisoformat(value)
    except ValueError:
        return "Use YYYY-MM-DD."
    if d > today:
        return "Date cannot be in the future."
    return None


def _validate_money(value, required: bool) -> Optional[str]:
    value = (value or "").strip() if isinstance(value, str) else value
    if not value:
        return "Required." if required else None
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return "Enter a valid number."
    if amount < 0:
        return "Cannot be negative."
    return None


# -- snapshot creation ------------------------------------------------------

def create_report(client: Client, form: Mapping[str, str]) -> tuple[Optional[QuarterlyReport], dict[str, str]]:
    """Validate, create QuarterlyReport + QuarterlyReportBalance rows,
    sync master Account latest values, then run the canonical
    snapshot-driven calculation engine to populate totals.

    Both the totals on the report and the snapshot rows are derived from
    the same source of truth, so create-time totals are guaranteed to
    match what a later `recalculate_report` would compute.
    """
    errors = validate(form, client)
    if errors:
        return None, errors

    report_date = date.fromisoformat(form["report_date"].strip())

    # Create the report shell with all totals at zero; the calculation
    # engine fills them in after balances are attached.
    report = QuarterlyReport(
        client_id=client.id,
        report_date=report_date,
        quarter_label=form["quarter_label"].strip(),
    )
    db.session.add(report)
    db.session.flush()

    for acct in client.accounts:
        prefix = f"account_{acct.id}"
        bal = Decimal((form.get(f"{prefix}_balance") or "0").strip())
        cash_raw = (form.get(f"{prefix}_cash_balance") or "").strip()
        cash = Decimal(cash_raw) if cash_raw else None
        date_raw = (form.get(f"{prefix}_date_updated") or "").strip()
        date_updated = date.fromisoformat(date_raw) if date_raw else report_date
        status = form.get(f"{prefix}_status").strip()

        # Append via the relationship so the new row is immediately visible
        # to compute_report_totals below without a separate DB round-trip.
        # IMPORTANT: pass account=acct (not just account_id) so the .account
        # relationship is populated in-memory — compute_report_totals reads
        # b.account.owner/category and would otherwise see None until flush.
        report.balances.append(QuarterlyReportBalance(
            account=acct,
            balance_at_report=bal,
            cash_balance_at_report=cash,
        ))

        # Sync master Account so the next entry starts from latest.
        acct.balance = bal
        acct.cash_balance = cash
        acct.date_updated = date_updated
        acct.status = status

    # Compute and persist totals from the just-attached snapshot rows.
    _apply_totals(report)
    db.session.commit()
    return report, {}


def recalculate_report(report: QuarterlyReport) -> None:
    """Recompute the QuarterlyReport totals from its (immutable) snapshot
    balances and the client's current SacsStatic record, then commit.

    Snapshot balances are NEVER modified by this call — only the derived
    totals on the report header row.
    """
    _apply_totals(report)
    db.session.commit()


def _apply_totals(report: QuarterlyReport) -> None:
    totals = calculations.compute_report_totals(report)
    for field, value in totals.items():
        setattr(report, field, value)
