from flask import Blueprint, flash, redirect, render_template, request, url_for

from extensions import db
from models import Account, Client
from services import account_service

bp = Blueprint("accounts", __name__)


@bp.route("/clients/<int:client_id>/accounts", methods=["GET", "POST"])
def index(client_id):
    client = db.get_or_404(Client, client_id)

    if request.method == "POST":
        account, errors = account_service.create_account(client, request.form)
        if not errors:
            flash(f"Added account '{_label(account)}'.", "success")
            return redirect(url_for("accounts.index", client_id=client.id))
        return _render_index(client, form=request.form, errors=errors), 400

    return _render_index(client)


@bp.route("/accounts/<int:account_id>/edit", methods=["GET", "POST"])
def edit(account_id):
    account = db.get_or_404(Account, account_id)

    if request.method == "POST":
        updated, errors = account_service.update_account(account, request.form)
        if not errors:
            flash(f"Updated account '{_label(updated)}'.", "success")
            return redirect(url_for("accounts.index", client_id=account.client_id))
        return render_template(
            "accounts/edit.html",
            account=account,
            client=account.client,
            form=request.form,
            errors=errors,
        ), 400

    return render_template(
        "accounts/edit.html",
        account=account,
        client=account.client,
        form=account_service.model_to_form(account),
        errors={},
    )


@bp.route("/accounts/<int:account_id>/delete", methods=["POST"])
def delete(account_id):
    account = db.get_or_404(Account, account_id)
    client_id = account.client_id
    label = _label(account)
    account_service.delete_account(account)
    flash(f"Deleted account '{label}'.", "success")
    return redirect(url_for("accounts.index", client_id=client_id))


def _render_index(client, form=None, errors=None):
    groups = account_service.group_for_display(client)
    totals = account_service.group_totals(groups)
    return render_template(
        "accounts/index.html",
        client=client,
        groups=groups,
        totals=totals,
        form=form if form is not None else _new_form_defaults(),
        errors=errors or {},
        had_form_post=form is not None,
    )


def _new_form_defaults() -> dict:
    from datetime import date
    return {
        "owner": "",
        "category": "",
        "account_type": "",
        "institution_name": "",
        "account_nickname": "",
        "account_last_four": "",
        "balance": "",
        "cash_balance": "",
        "interest_rate": "",
        "date_updated": date.today().isoformat(),
        "status": "up_to_date",
    }


def _label(account: Account) -> str:
    bits = [account.account_type or "Account"]
    name = account.institution_name or account.account_nickname
    if name:
        bits.append(name)
    if account.account_last_four:
        bits.append(f"x{account.account_last_four}")
    return " · ".join(bits)
