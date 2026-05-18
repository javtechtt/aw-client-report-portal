from flask import Blueprint, jsonify, render_template

from models import Client

bp = Blueprint("dashboard", __name__)


@bp.route("/")
def index():
    clients = Client.query.order_by(Client.household_name).all()
    return render_template("dashboard.html", clients=clients)


@bp.route("/healthz")
def healthz():
    return jsonify(status="ok")
