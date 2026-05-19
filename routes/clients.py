from flask import Blueprint, flash, redirect, render_template, request, url_for

from extensions import db
from models import Client
from services import account_service, client_service

bp = Blueprint("clients", __name__, url_prefix="/clients")


@bp.route("/new", methods=["GET", "POST"])
def new():
    if request.method == "POST":
        client, errors = client_service.create_household(request.form)
        if not errors:
            flash(f"Created household '{client.household_name}'.", "success")
            return redirect(url_for("clients.show", client_id=client.id))
        return render_template(
            "clients/new.html",
            form=request.form,
            errors=errors,
        ), 400

    return render_template(
        "clients/new.html",
        form={"client_type": "single", "floor_amount": "1000.00"},
        errors={},
    )


@bp.route("/<int:client_id>")
def show(client_id):
    client = db.get_or_404(Client, client_id)
    groups = account_service.group_for_display(client)
    totals = account_service.group_totals(groups)
    return render_template(
        "clients/show.html",
        client=client,
        groups=groups,
        totals=totals,
    )


@bp.route("/<int:client_id>/edit", methods=["GET", "POST"])
def edit(client_id):
    client = db.get_or_404(Client, client_id)

    if request.method == "POST":
        updated, errors = client_service.update_household(client, request.form)
        if not errors:
            flash(f"Updated household '{updated.household_name}'.", "success")
            return redirect(url_for("clients.show", client_id=updated.id))
        return render_template(
            "clients/edit.html",
            client=client,
            form=request.form,
            errors=errors,
        ), 400

    return render_template(
        "clients/edit.html",
        client=client,
        form=client_service.model_to_form(client),
        errors={},
    )
