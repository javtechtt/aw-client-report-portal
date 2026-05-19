"""Client / household domain service.

Owns validation, creation, and editing of Client + Person + SacsStatic
records. Routes stay thin and delegate here. All monetary input is parsed
through Decimal (never float) per project policy.
"""
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Mapping, Optional

from extensions import db
from models import CLIENT_TYPES, Client, Person, SacsStatic

OPTIONAL_MONEY_FIELDS = (
    "client_1_monthly_salary",
    "client_2_monthly_salary",
    "floor_amount",
    "insurance_deductibles_total",
    "private_reserve_target",
)


def validate(form: Mapping[str, str]) -> dict[str, str]:
    errors: dict[str, str] = {}
    today = date.today()

    if not (form.get("household_name") or "").strip():
        errors["household_name"] = "Required."

    client_type = (form.get("client_type") or "").strip()
    if client_type not in CLIENT_TYPES:
        errors["client_type"] = "Select Single or Married."
    is_married = client_type == "married"

    # Client 1 is always required.
    if not (form.get("client_1_full_name") or "").strip():
        errors["client_1_full_name"] = "Required."

    err = _validate_dob(form.get("client_1_dob"), today, required=True)
    if err:
        errors["client_1_dob"] = err

    err = _validate_ssn(form.get("client_1_ssn_last_four"), required=True)
    if err:
        errors["client_1_ssn_last_four"] = err

    # Client 2: required name+DOB only when married; SSN optional in either case
    # but format-checked if provided.
    if is_married:
        if not (form.get("client_2_full_name") or "").strip():
            errors["client_2_full_name"] = "Required for married households."
        err = _validate_dob(form.get("client_2_dob"), today, required=True)
        if err:
            errors["client_2_dob"] = err
    else:
        if (form.get("client_2_dob") or "").strip():
            err = _validate_dob(form.get("client_2_dob"), today, required=False)
            if err:
                errors["client_2_dob"] = err

    if (form.get("client_2_ssn_last_four") or "").strip():
        err = _validate_ssn(form.get("client_2_ssn_last_four"), required=False)
        if err:
            errors["client_2_ssn_last_four"] = err

    err = _validate_money(form.get("monthly_outflow_budget"), required=True)
    if err:
        errors["monthly_outflow_budget"] = err

    for field in OPTIONAL_MONEY_FIELDS:
        err = _validate_money(form.get(field), required=False)
        if err:
            errors[field] = err

    return errors


def create_household(form: Mapping[str, str]) -> tuple[Optional[Client], dict[str, str]]:
    errors = validate(form)
    if errors:
        return None, errors

    client = Client(
        household_name=form["household_name"].strip(),
        client_type=form["client_type"].strip(),
    )
    _apply_persons(client, form)
    _apply_sacs(client, form)
    db.session.add(client)
    db.session.commit()
    return client, {}


def update_household(client: Client, form: Mapping[str, str]) -> tuple[Optional[Client], dict[str, str]]:
    errors = validate(form)
    if errors:
        return None, errors

    client.household_name = form["household_name"].strip()
    client.client_type = form["client_type"].strip()
    _apply_persons(client, form)
    _apply_sacs(client, form)
    db.session.commit()
    return client, {}


def model_to_form(client: Client) -> dict:
    """Build a form-shaped dict from a Client for pre-filling the edit form."""
    persons = {p.role: p for p in client.persons}
    c1 = persons.get("client_1")
    c2 = persons.get("client_2")
    s = client.sacs_static

    return {
        "household_name": client.household_name or "",
        "client_type": client.client_type or "single",
        "client_1_full_name": c1.full_name if c1 else "",
        "client_1_dob": c1.dob.isoformat() if c1 else "",
        "client_1_ssn_last_four": c1.ssn_last_four if c1 else "",
        "client_2_full_name": c2.full_name if c2 else "",
        "client_2_dob": c2.dob.isoformat() if c2 else "",
        "client_2_ssn_last_four": c2.ssn_last_four if c2 else "",
        "client_1_monthly_salary": _money_str(s.client_1_monthly_salary) if s else "",
        "client_2_monthly_salary": _money_str(s.client_2_monthly_salary) if s else "",
        "monthly_outflow_budget": _money_str(s.monthly_outflow_budget) if s else "",
        "floor_amount": _money_str(s.floor_amount) if s else "1000.00",
        "insurance_deductibles_total": _money_str(s.insurance_deductibles_total) if s else "",
        "private_reserve_target": _money_str(s.private_reserve_target) if s else "",
    }


# -- internals --------------------------------------------------------------

def _apply_persons(client: Client, form: Mapping[str, str]) -> None:
    # Reconcile persons by role rather than wipe-and-recreate so that future
    # FKs (e.g. quarterly_report_balances referencing person IDs in later
    # phases) remain stable across edits.
    existing = {p.role: p for p in client.persons}

    c1 = existing.get("client_1") or Person(role="client_1")
    c1.full_name = form["client_1_full_name"].strip()
    c1.dob = date.fromisoformat(form["client_1_dob"])
    c1.ssn_last_four = form["client_1_ssn_last_four"].strip()
    if c1 not in client.persons:
        client.persons.append(c1)

    if form["client_type"].strip() == "married":
        c2 = existing.get("client_2") or Person(role="client_2")
        c2.full_name = form["client_2_full_name"].strip()
        c2.dob = date.fromisoformat(form["client_2_dob"])
        c2.ssn_last_four = (form.get("client_2_ssn_last_four") or "").strip()
        if c2 not in client.persons:
            client.persons.append(c2)
    elif "client_2" in existing:
        # Married -> single transition: drop the second person.
        client.persons.remove(existing["client_2"])
        db.session.delete(existing["client_2"])


def _apply_sacs(client: Client, form: Mapping[str, str]) -> None:
    sacs = client.sacs_static or SacsStatic()

    sacs.client_1_monthly_salary = _decimal_or(form.get("client_1_monthly_salary"), Decimal("0"))
    sacs.client_2_monthly_salary = _decimal_optional(form.get("client_2_monthly_salary"))
    sacs.monthly_outflow_budget = _decimal_or(form.get("monthly_outflow_budget"), Decimal("0"))
    sacs.floor_amount = _decimal_or(form.get("floor_amount"), Decimal("1000"))
    sacs.insurance_deductibles_total = _decimal_or(form.get("insurance_deductibles_total"), Decimal("0"))
    sacs.private_reserve_target = _decimal_or(form.get("private_reserve_target"), Decimal("0"))

    if client.sacs_static is None:
        client.sacs_static = sacs


def _validate_dob(value, today: date, required: bool) -> Optional[str]:
    value = (value or "").strip()
    if not value:
        return "Required." if required else None
    try:
        dob = date.fromisoformat(value)
    except ValueError:
        return "Use the date picker (YYYY-MM-DD)."
    if dob > today:
        return "Date cannot be in the future."
    return None


def _validate_ssn(value, required: bool) -> Optional[str]:
    value = (value or "").strip()
    if not value:
        return "Required." if required else None
    if len(value) != 4 or not value.isdigit():
        return "Must be exactly 4 digits."
    return None


def _validate_money(value, required: bool) -> Optional[str]:
    value = (value or "").strip()
    if not value:
        return "Required." if required else None
    try:
        amount = Decimal(value)
    except (InvalidOperation, ValueError):
        return "Enter a valid number."
    if amount < 0:
        return "Cannot be negative."
    return None


def _decimal_or(value, default: Decimal) -> Decimal:
    value = (value or "").strip() if isinstance(value, str) else value
    if value is None or value == "":
        return default
    return Decimal(str(value))


def _decimal_optional(value) -> Optional[Decimal]:
    value = (value or "").strip() if isinstance(value, str) else value
    if value is None or value == "":
        return None
    return Decimal(str(value))


def _money_str(value) -> str:
    if value is None:
        return ""
    return f"{Decimal(value):.2f}"
