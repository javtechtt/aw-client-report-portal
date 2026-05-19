"""Idempotent seed for the AW Client Report Portal.

Inserts three CLEARLY FAKE sample households spanning the layout edge cases.
The Stress-Test sample exists permanently to exercise the TCC dynamic bubble
grid every time the app loads.

Naming/data conventions are deliberate: see project memory
`feedback_seed_data_fake`. Use this file as the canonical example when
adding more samples.
"""
from datetime import date
from decimal import Decimal

from extensions import db
from models import Account, Client, Person, SacsStatic


def run():
    """Destructive reseed — wipes all clients and reinserts the three
    sample households. Used by `flask --app app seed` for developer reset."""
    # Wipe via ORM so cascade="all, delete-orphan" fires correctly.
    for c in Client.query.all():
        db.session.delete(c)
    db.session.commit()

    _single_sample()
    _married_sample()
    _stress_test_sample()

    db.session.commit()


def seed_if_empty() -> bool:
    """Insert the three sample households only when the database has no
    clients yet. Safe to call on every app boot — once real data exists,
    this becomes a no-op and never touches it.

    Returns True if seeding ran, False if skipped.
    """
    if Client.query.count() > 0:
        return False

    _single_sample()
    _married_sample()
    _stress_test_sample()
    db.session.commit()
    return True


def _single_sample():
    c = Client(household_name="Sample Single Household", client_type="single")
    c.persons.append(Person(
        role="client_1", full_name="Sample Single A",
        dob=date(1980, 1, 1), ssn_last_four="0001",
    ))
    c.sacs_static = SacsStatic(
        client_1_monthly_salary=Decimal("8000.00"),
        monthly_outflow_budget=Decimal("5000.00"),
        floor_amount=Decimal("1000.00"),
        insurance_deductibles_total=Decimal("3000.00"),
        private_reserve_target=Decimal("33000.00"),  # 6 * 5000 + 3000
    )
    c.accounts.extend([
        Account(owner="client_1", category="retirement", account_type="IRA",
                institution_name="Sample Brokerage", account_nickname="Sample IRA",
                account_last_four="0001", balance=Decimal("45000.00"),
                date_updated=date(2026, 4, 1), status="up_to_date"),
        Account(owner="client_1", category="non_retirement",
                account_type="Checking", institution_name="Sample Bank",
                account_nickname="Sample Checking", account_last_four="0002",
                balance=Decimal("12000.00"), date_updated=date(2026, 4, 1),
                status="up_to_date"),
    ])
    db.session.add(c)


def _married_sample():
    """Modeled loosely on the TCC reference screenshot's account shape (so
    Phases 6/7 have realistic data to render against), but all numbers and
    names are flagged as Sample.
    """
    c = Client(household_name="Sample Married Household", client_type="married")
    c.persons.extend([
        Person(role="client_1", full_name="Sample Married A",
               dob=date(1975, 6, 15), ssn_last_four="0001"),
        Person(role="client_2", full_name="Sample Married B",
               dob=date(1978, 9, 22), ssn_last_four="0002"),
    ])
    c.sacs_static = SacsStatic(
        client_1_monthly_salary=Decimal("8000.00"),
        client_2_monthly_salary=Decimal("7000.00"),
        monthly_outflow_budget=Decimal("12000.00"),
        floor_amount=Decimal("1000.00"),
        insurance_deductibles_total=Decimal("5000.00"),
        private_reserve_target=Decimal("77000.00"),  # 6 * 12000 + 5000
    )
    c.accounts.extend([
        Account(owner="client_1", category="retirement", account_type="ROTH IRA",
                institution_name="Sample Brokerage", account_last_four="0001",
                balance=Decimal("11162.47"), cash_balance=Decimal("316.00"),
                date_updated=date(2025, 7, 25), status="up_to_date"),
        Account(owner="client_1", category="retirement", account_type="IRA",
                institution_name="Sample Brokerage", account_last_four="0002",
                balance=Decimal("0.00"), date_updated=date(2025, 7, 25),
                status="up_to_date"),
        Account(owner="client_2", category="retirement", account_type="IRA",
                institution_name="Sample Brokerage", account_last_four="0003",
                balance=Decimal("37232.46"), cash_balance=Decimal("1543.00"),
                date_updated=date(2025, 7, 25), status="up_to_date"),
        Account(owner="client_2", category="retirement", account_type="401K",
                institution_name="Sample 401K Provider", account_last_four="0004",
                balance=Decimal("70042.00"), date_updated=date(2025, 4, 1),
                status="stale"),
        Account(owner="client_2", category="retirement", account_type="ROTH IRA",
                institution_name="Sample Brokerage", account_last_four="0005",
                balance=Decimal("18885.93"), cash_balance=Decimal("508.00"),
                date_updated=date(2025, 7, 25), status="up_to_date"),
        Account(owner="joint", category="non_retirement", account_type="Checking",
                institution_name="Sample Bank", account_nickname="Main Checking",
                account_last_four="0006", balance=Decimal("448.28"),
                date_updated=date(2025, 5, 23), status="up_to_date"),
        Account(owner="joint", category="non_retirement", account_type="Savings",
                institution_name="Sample Bank", account_last_four="0007",
                balance=Decimal("44.02"), date_updated=date(2025, 5, 23),
                status="up_to_date"),
        Account(owner="joint", category="non_retirement", account_type="FICA",
                institution_name="Sample FICA Custodian", account_last_four="0008",
                balance=Decimal("44067.78"), date_updated=date(2025, 7, 25),
                status="up_to_date"),
        Account(owner="joint", category="non_retirement", account_type="JT TEN",
                institution_name="Sample Brokerage", account_last_four="0009",
                balance=Decimal("0.00"), date_updated=date(2025, 7, 25),
                status="up_to_date"),
        Account(owner="trust", category="trust", account_type="Family Trust",
                institution_name="Self-Custody",
                account_nickname="Sample Family Trust",
                account_last_four="0010", balance=Decimal("450000.00"),
                date_updated=date(2025, 7, 25), status="up_to_date"),
        Account(owner="joint", category="liability", account_type="Primary Mortgage",
                institution_name="Sample Mortgage Co", account_last_four="0011",
                balance=Decimal("224219.24"), interest_rate=Decimal("0.0625"),
                date_updated=date(2025, 7, 25), status="up_to_date"),
        Account(owner="joint", category="liability", account_type="Auto Loan",
                institution_name="Sample Auto Finance",
                account_nickname="Sample Sedan", account_last_four="0012",
                balance=Decimal("25992.00"), interest_rate=Decimal("0.0499"),
                date_updated=date(2025, 7, 25), status="up_to_date"),
    ])
    db.session.add(c)


def _stress_test_sample():
    """Married, 5 retirement per spouse, 6 non-retirement, trust, 3 liabilities.
    Permanent stress test for the TCC dynamic bubble grid (see Phase 1 plan,
    TCC layout strategy section).
    """
    c = Client(household_name="Stress-Test Sample Household", client_type="married")
    c.persons.extend([
        Person(role="client_1", full_name="Stress-Test A",
               dob=date(1970, 3, 10), ssn_last_four="9998"),
        Person(role="client_2", full_name="Stress-Test B",
               dob=date(1972, 11, 5), ssn_last_four="9999"),
    ])
    c.sacs_static = SacsStatic(
        client_1_monthly_salary=Decimal("20000.00"),
        client_2_monthly_salary=Decimal("15000.00"),
        monthly_outflow_budget=Decimal("25000.00"),
        floor_amount=Decimal("1000.00"),
        insurance_deductibles_total=Decimal("12000.00"),
        private_reserve_target=Decimal("162000.00"),  # 6 * 25000 + 12000
    )
    retirement_types = ["IRA", "ROTH IRA", "401K", "SEP IRA", "Pension"]
    non_ret_types = ["Brokerage", "Checking", "Savings", "FICA", "HYSA", "CD"]

    for i, t in enumerate(retirement_types, start=1):
        c.accounts.append(Account(
            owner="client_1", category="retirement", account_type=t,
            institution_name="Sample Brokerage",
            account_last_four=f"100{i}", balance=Decimal(f"{i * 50000}.00"),
            date_updated=date(2026, 4, 1), status="up_to_date",
        ))
    for i, t in enumerate(retirement_types, start=1):
        c.accounts.append(Account(
            owner="client_2", category="retirement", account_type=t,
            institution_name="Sample Brokerage",
            account_last_four=f"200{i}", balance=Decimal(f"{i * 40000}.00"),
            date_updated=date(2026, 4, 1), status="up_to_date",
        ))
    for i, t in enumerate(non_ret_types, start=1):
        c.accounts.append(Account(
            owner="joint", category="non_retirement", account_type=t,
            institution_name="Sample Bank",
            account_last_four=f"300{i}", balance=Decimal(f"{i * 10000}.00"),
            date_updated=date(2026, 4, 1), status="up_to_date",
        ))
    c.accounts.append(Account(
        owner="trust", category="trust", account_type="Family Trust",
        institution_name="Self-Custody", account_last_four="0010",
        balance=Decimal("1200000.00"), date_updated=date(2026, 4, 1),
        status="up_to_date",
    ))
    for i, t in enumerate(["Primary Mortgage", "Auto Loan", "HELOC"], start=1):
        c.accounts.append(Account(
            owner="joint", category="liability", account_type=t,
            institution_name="Sample Lender",
            account_last_four=f"400{i}", balance=Decimal(f"{i * 100000}.00"),
            interest_rate=Decimal("0.0500"), date_updated=date(2026, 4, 1),
            status="up_to_date",
        ))
    db.session.add(c)


if __name__ == "__main__":
    from app import create_app
    app = create_app()
    with app.app_context():
        run()
        print("Seed complete: 3 sample households inserted.")
