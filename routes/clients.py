from flask import Blueprint, render_template

bp = Blueprint("clients", __name__, url_prefix="/clients")


@bp.route("/new", methods=["GET", "POST"])
def new():
    return render_template("_placeholder.html", phase=2, feature="Add Client")


@bp.route("/<int:client_id>")
def show(client_id):
    return render_template("_placeholder.html", phase=2, feature="Client Detail")


@bp.route("/<int:client_id>/edit", methods=["GET", "POST"])
def edit(client_id):
    return render_template("_placeholder.html", phase=2, feature="Edit Client")
