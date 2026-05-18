from flask import Blueprint, render_template

bp = Blueprint("reports", __name__)


@bp.route("/clients/<int:client_id>/reports/new", methods=["GET", "POST"])
def new(client_id):
    return render_template("_placeholder.html", phase=4, feature="Quarterly Report Entry")


@bp.route("/reports/<int:report_id>")
def review(report_id):
    return render_template("_placeholder.html", phase=5, feature="Calculation Review")


@bp.route("/reports/<int:report_id>/sacs")
def sacs_preview(report_id):
    return render_template("_placeholder.html", phase=6, feature="SACS Preview")


@bp.route("/reports/<int:report_id>/tcc")
def tcc_preview(report_id):
    return render_template("_placeholder.html", phase=7, feature="TCC Preview")


@bp.route("/reports/<int:report_id>/sacs.pdf")
def sacs_pdf(report_id):
    return render_template("_placeholder.html", phase=8, feature="SACS PDF Download")


@bp.route("/reports/<int:report_id>/tcc.pdf")
def tcc_pdf(report_id):
    return render_template("_placeholder.html", phase=8, feature="TCC PDF Download")


@bp.route("/reports")
def history():
    return render_template("_placeholder.html", phase=8, feature="Report History")
