"""Account domain service.

Owns validation, CRUD, and grouping of Account records. Enforces the
business rules from PRD §2b about which owners are allowed under which
categories. All money is Decimal (never float) per project policy.

The `group_for_display` function returns the exact buckets used by the
TCC report (Phase 7), so Phase 3 and Phase 7 share one source of truth.
"""
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Iterable, Mapping, Optional

from extensions import db
from models import (
    ACCOUNT_CATEGORIES,
    ACCOUNT_OWNERS,
    ACCOUNT_STATUSES,
    Account,
    Client,
)

ACCOUNT_TYPES = (
    "IRA",
    "Roth IRA",
    "401K",
    "Pension",
    "Brokerage",
    "Checking",
    "Savings",
    "Money Market",
    "Trust Property",
    "Mortgage",
    "Auto Loan",
    "Other",
)

INVESTMENT_TYPES = frozenset({"IRA", "Roth IRA", "401K", "Pension", "Brokerage", "Money Market"})

# Which owners are allowed for each category. Enforced server-side; the JS
# form mirrors these for UX but server is authoritative.
OWNER_RULES = {
    "retirement":     {"client_1", "client_2"},
    "non_retirement": {"client_1", "client_2", "joint"},
    "trust":          {"trust"},
    "liability":      {"client_1", "client_2", "joint", "trust"},
}

STATUS_LABELS = {
    "up_to_date": "Up to date",
    "stale":      "Stale",
    "missing":    "Missing",
}

OWNER_LABELS = {
    "client_1": "Client 1",
    "client_2": "Client 2",
    "joint":    "Joint",
    "trust":    "Trust",
}


# -- validation -------------------------------------------------------------

def validate(form: Mapping[str, str], client: Client) -> dict[str, str]:
    errors: dict[str, str] = {}
    today = date.today()

    owner = (form.get("owner") or "").strip()
    category = (form.get("category") or "").strip()
    account_type = (form.get("account_type") or "").strip()

    if owner not in ACCOUNT_OWNERS:
        errors["owner"] = "Required."
    if category not in ACCOUNT_CATEGORIES:
        errors["category"] = "Required."
    if not account_type:
        errors["account_type"] = "Required."

    # Owner / category compatibility (PRD business rules).
    if owner in ACCOUNT_OWNERS and category in ACCOUNT_CATEGORIES:
        if owner not in OWNER_RULES[category]:
            errors["owner"] = _owner_rule_message(category)

    # Single-household households cannot own a client_2 account.
    if client.client_type == "single" and owner == "client_2":
        errors["owner"] = "This household has no Client 2."

    if not (form.get("institution_name") or "").strip() and not (form.get("account_nickname") or "").strip():
        errors["institution_name"] = "Institution name or nickname is required."

    err = _validate_money(form.get("balance"), required=True, allow_zero=True)
    if err:
        errors["balance"] = err

    if (form.get("cash_balance") or "").strip():
        err = _validate_money(form.get("cash_balance"), required=False, allow_zero=True)
        if err:
            errors["cash_balance"] = err

    if (form.get("interest_rate") or "").strip():
        err = _validate_rate(form.get("interest_rate"))
        if err:
            errors["interest_rate"] = err

    last_four = (form.get("account_last_four") or "").strip()
    if last_four:
        if len(last_four) != 4 or not last_four.isdigit():
            errors["account_last_four"] = "Must be exactly 4 digits."

    if (form.get("date_updated") or "").strip():
        try:
            d = date.fromisoformat(form["date_updated"].strip())
            if d > today:
                errors["date_updated"] = "Date cannot be in the future."
        except ValueError:
            errors["date_updated"] = "Use the date picker (YYYY-MM-DD)."

    status = (form.get("status") or "").strip()
    if status not in ACCOUNT_STATUSES:
        errors["status"] = "Required."

    return errors


def _owner_rule_message(category: str) -> str:
    allowed = OWNER_RULES.get(category, set())
    nice = ", ".join(OWNER_LABELS[o] for o in ("client_1", "client_2", "joint", "trust") if o in allowed)
    return f"Owner not allowed for category '{category}'. Allowed: {nice}."


def _validate_money(value, required: bool, allow_zero: bool = True) -> Optional[str]:
    value = (value or "").strip() if isinstance(value, str) else value
    if not value and value != 0:
        return "Required." if required else None
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return "Enter a valid number."
    if amount < 0:
        return "Cannot be negative."
    if not allow_zero and amount == 0:
        return "Must be greater than zero."
    return None


def _validate_rate(value) -> Optional[str]:
    try:
        rate = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return "Enter a valid number."
    if rate < 0:
        return "Cannot be negative."
    return None


# -- CRUD -------------------------------------------------------------------

def create_account(client: Client, form: Mapping[str, str]) -> tuple[Optional[Account], dict[str, str]]:
    errors = validate(form, client)
    if errors:
        return None, errors

    account = Account(client_id=client.id)
    _apply_form(account, form)
    db.session.add(account)
    db.session.commit()
    return account, {}


def update_account(account: Account, form: Mapping[str, str]) -> tuple[Optional[Account], dict[str, str]]:
    errors = validate(form, account.client)
    if errors:
        return None, errors

    _apply_form(account, form)
    db.session.commit()
    return account, {}


def delete_account(account: Account) -> None:
    db.session.delete(account)
    db.session.commit()


def _apply_form(account: Account, form: Mapping[str, str]) -> None:
    account.owner = form["owner"].strip()
    account.category = form["category"].strip()
    account.account_type = form["account_type"].strip()
    account.institution_name = (form.get("institution_name") or "").strip() or None
    account.account_nickname = (form.get("account_nickname") or "").strip() or None
    account.account_last_four = (form.get("account_last_four") or "").strip() or None
    account.balance = Decimal((form.get("balance") or "0").strip())

    cash = (form.get("cash_balance") or "").strip()
    account.cash_balance = Decimal(cash) if cash else None

    rate = (form.get("interest_rate") or "").strip()
    account.interest_rate = Decimal(rate) if rate else None

    date_str = (form.get("date_updated") or "").strip()
    account.date_updated = date.fromisoformat(date_str) if date_str else date.today()

    account.status = form["status"].strip()


# -- form pre-fill ----------------------------------------------------------

def model_to_form(account: Account) -> dict:
    return {
        "owner": account.owner,
        "category": account.category,
        "account_type": account.account_type or "",
        "institution_name": account.institution_name or "",
        "account_nickname": account.account_nickname or "",
        "account_last_four": account.account_last_four or "",
        "balance": _money_str(account.balance),
        "cash_balance": _money_str(account.cash_balance) if account.cash_balance is not None else "",
        "interest_rate": _rate_str(account.interest_rate) if account.interest_rate is not None else "",
        "date_updated": account.date_updated.isoformat() if account.date_updated else "",
        "status": account.status,
    }


def _money_str(value) -> str:
    if value is None:
        return ""
    return f"{Decimal(value):.2f}"


def _rate_str(value) -> str:
    if value is None:
        return ""
    # Stored as decimal fraction (0.0625 = 6.25%); display with 4 decimals.
    return f"{Decimal(value):.4f}"


# -- grouping for display + future TCC consumption --------------------------

def group_for_display(client: Client) -> dict:
    """Buckets a household's accounts the way the Manage Accounts page and
    the TCC report both consume.

    Returned shape:
        {
            "client_1_retirement": [Account, ...],
            "client_2_retirement": [Account, ...],
            "non_retirement":      [Account, ...],   # excludes trust per PRD
            "trust":               [Account, ...],
            "liabilities":         [Account, ...],
        }

    The order within each list is stable (by id) so the UI doesn't shuffle.
    """
    groups: dict[str, list[Account]] = {
        "client_1_retirement": [],
        "client_2_retirement": [],
        "non_retirement":      [],
        "trust":               [],
        "liabilities":         [],
    }
    for acct in sorted(client.accounts, key=lambda a: a.id):
        if acct.category == "retirement" and acct.owner == "client_1":
            groups["client_1_retirement"].append(acct)
        elif acct.category == "retirement" and acct.owner == "client_2":
            groups["client_2_retirement"].append(acct)
        elif acct.category == "non_retirement":
            groups["non_retirement"].append(acct)
        elif acct.category == "trust":
            groups["trust"].append(acct)
        elif acct.category == "liability":
            groups["liabilities"].append(acct)
    return groups


def group_totals(groups: dict[str, list[Account]]) -> dict[str, Decimal]:
    """Sum of balances per group. Used for in-section subtotals on the
    Manage Accounts page; the canonical TCC math lives in Phase 5."""
    def _sum(accs: Iterable[Account]) -> Decimal:
        total = Decimal("0")
        for a in accs:
            if a.balance is not None:
                total += a.balance
        return total
    return {key: _sum(accs) for key, accs in groups.items()}
