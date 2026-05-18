from flask import Blueprint, render_template

bp = Blueprint("accounts", __name__)


@bp.route("/clients/<int:client_id>/accounts", methods=["GET", "POST"])
def index(client_id):
    return render_template("_placeholder.html", phase=3, feature="Account Management")


@bp.route("/accounts/<int:account_id>/edit", methods=["GET", "POST"])
def edit(account_id):
    return render_template("_placeholder.html", phase=3, feature="Edit Account")


@bp.route("/accounts/<int:account_id>/delete", methods=["POST"])
def delete(account_id):
    return render_template("_placeholder.html", phase=3, feature="Delete Account")
