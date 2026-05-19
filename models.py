from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint

from extensions import db

CLIENT_TYPES = ("single", "married")
PERSON_ROLES = ("client_1", "client_2")
ACCOUNT_OWNERS = ("client_1", "client_2", "joint", "trust")
ACCOUNT_CATEGORIES = ("retirement", "non_retirement", "trust", "liability")
ACCOUNT_STATUSES = ("up_to_date", "stale", "missing")


def _enum_check(column, values, name):
    quoted = ", ".join(f"'{v}'" for v in values)
    return CheckConstraint(f"{column} IN ({quoted})", name=name)


class Client(db.Model):
    __tablename__ = "clients"

    id = db.Column(db.Integer, primary_key=True)
    household_name = db.Column(db.String(120), nullable=False)
    client_type = db.Column(db.String(16), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    persons = db.relationship(
        "Person", backref="client", cascade="all, delete-orphan",
        order_by="Person.role",
    )
    accounts = db.relationship(
        "Account", backref="client", cascade="all, delete-orphan",
    )
    sacs_static = db.relationship(
        "SacsStatic", backref="client", uselist=False, cascade="all, delete-orphan",
    )
    reports = db.relationship(
        "QuarterlyReport", backref="client", cascade="all, delete-orphan",
        order_by="QuarterlyReport.report_date.desc()",
    )

    __table_args__ = (
        _enum_check("client_type", CLIENT_TYPES, "client_type_check"),
    )

    @property
    def last_report_date(self):
        return self.reports[0].report_date if self.reports else None

    def __repr__(self):
        return f"<Client {self.household_name!r}>"


class Person(db.Model):
    __tablename__ = "persons"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    role = db.Column(db.String(16), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    dob = db.Column(db.Date, nullable=False)
    ssn_last_four = db.Column(db.String(4), nullable=False)

    __table_args__ = (
        _enum_check("role", PERSON_ROLES, "person_role_check"),
    )

    @property
    def age(self):
        today = date.today()
        years = today.year - self.dob.year
        if (today.month, today.day) < (self.dob.month, self.dob.day):
            years -= 1
        return years


class Account(db.Model):
    __tablename__ = "accounts"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    owner = db.Column(db.String(16), nullable=False)
    category = db.Column(db.String(20), nullable=False)
    account_type = db.Column(db.String(64), nullable=False)
    institution_name = db.Column(db.String(120))
    account_nickname = db.Column(db.String(120))
    account_last_four = db.Column(db.String(4))
    balance = db.Column(db.Numeric(14, 2), nullable=False, default=Decimal("0"))
    cash_balance = db.Column(db.Numeric(14, 2))
    interest_rate = db.Column(db.Numeric(6, 4))
    date_updated = db.Column(db.Date)
    status = db.Column(db.String(16), nullable=False, default="up_to_date")

    __table_args__ = (
        _enum_check("owner", ACCOUNT_OWNERS, "account_owner_check"),
        _enum_check("category", ACCOUNT_CATEGORIES, "account_category_check"),
        _enum_check("status", ACCOUNT_STATUSES, "account_status_check"),
    )


class SacsStatic(db.Model):
    __tablename__ = "sacs_static"

    client_id = db.Column(db.Integer, db.ForeignKey("clients.id", ondelete="CASCADE"), primary_key=True)
    client_1_monthly_salary = db.Column(db.Numeric(14, 2), nullable=False, default=Decimal("0"))
    client_2_monthly_salary = db.Column(db.Numeric(14, 2))
    monthly_outflow_budget = db.Column(db.Numeric(14, 2), nullable=False, default=Decimal("0"))
    floor_amount = db.Column(db.Numeric(14, 2), nullable=False, default=Decimal("1000"))
    insurance_deductibles_total = db.Column(db.Numeric(14, 2), nullable=False, default=Decimal("0"))
    private_reserve_target = db.Column(db.Numeric(14, 2), nullable=False, default=Decimal("0"))


class QuarterlyReport(db.Model):
    __tablename__ = "quarterly_reports"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    report_date = db.Column(db.Date, nullable=False)
    quarter_label = db.Column(db.String(16), nullable=False)
    total_inflow = db.Column(db.Numeric(14, 2), nullable=False, default=Decimal("0"))
    total_outflow = db.Column(db.Numeric(14, 2), nullable=False, default=Decimal("0"))
    excess_transfer = db.Column(db.Numeric(14, 2), nullable=False, default=Decimal("0"))
    private_reserve_target = db.Column(db.Numeric(14, 2), nullable=False, default=Decimal("0"))
    client_1_retirement_total = db.Column(db.Numeric(14, 2), nullable=False, default=Decimal("0"))
    client_2_retirement_total = db.Column(db.Numeric(14, 2), nullable=False, default=Decimal("0"))
    non_retirement_total = db.Column(db.Numeric(14, 2), nullable=False, default=Decimal("0"))
    trust_total = db.Column(db.Numeric(14, 2), nullable=False, default=Decimal("0"))
    grand_total = db.Column(db.Numeric(14, 2), nullable=False, default=Decimal("0"))
    liabilities_total = db.Column(db.Numeric(14, 2), nullable=False, default=Decimal("0"))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    balances = db.relationship(
        "QuarterlyReportBalance", backref="report", cascade="all, delete-orphan",
    )


class QuarterlyReportBalance(db.Model):
    __tablename__ = "quarterly_report_balances"

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey("quarterly_reports.id", ondelete="CASCADE"), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey("accounts.id"), nullable=False)
    balance_at_report = db.Column(db.Numeric(14, 2), nullable=False)
    cash_balance_at_report = db.Column(db.Numeric(14, 2))

    # One-way relationship so report snapshots can render account metadata
    # (type, owner, last-four) without a separate lookup. Note: master
    # Account rows can be edited after a snapshot is captured, so derived
    # display values may drift over time — true immutability of these
    # fields would require snapshotting them in additional columns. Phase 8
    # report history can revisit this.
    account = db.relationship("Account", foreign_keys=[account_id])
