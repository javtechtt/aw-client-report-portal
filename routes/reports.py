from flask import Blueprint, Response, current_app, flash, redirect, render_template, request, url_for

from extensions import db
from models import Client, QuarterlyReport
from services import pdf_service, report_builder, report_entry_service

bp = Blueprint("reports", __name__)


@bp.route("/clients/<int:client_id>/reports/new", methods=["GET", "POST"])
def new(client_id):
    client = db.get_or_404(Client, client_id)

    if not client.accounts:
        flash(
            "Add at least one account before creating a quarterly report.",
            "error",
        )
        return redirect(url_for("accounts.index", client_id=client.id))

    if request.method == "POST":
        report, errors = report_entry_service.create_report(client, request.form)
        if not errors:
            flash(
                f"Created {report.quarter_label} snapshot for {client.household_name}.",
                "success",
            )
            return redirect(url_for("reports.review", report_id=report.id))
        return _render_new(client, form=request.form, errors=errors), 400

    return _render_new(client)


@bp.route("/reports/<int:report_id>")
def review(report_id):
    report = db.get_or_404(QuarterlyReport, report_id)
    ctx = report_builder.build_review_context(report)
    return render_template("reports/show.html", **ctx)


@bp.route("/reports/<int:report_id>/recalculate", methods=["POST"])
def recalculate(report_id):
    report = db.get_or_404(QuarterlyReport, report_id)
    report_entry_service.recalculate_report(report)
    flash(f"Recalculated totals for {report.quarter_label}.", "success")
    return redirect(url_for("reports.review", report_id=report.id))


@bp.route("/reports/<int:report_id>/sacs")
def sacs_preview(report_id):
    report = db.get_or_404(QuarterlyReport, report_id)
    ctx = report_builder.prepare_sacs_context(report)
    return render_template("reports/sacs.html", **ctx)


@bp.route("/reports/<int:report_id>/tcc")
def tcc_preview(report_id):
    report = db.get_or_404(QuarterlyReport, report_id)
    ctx = report_builder.prepare_tcc_context(report)
    return render_template("reports/tcc.html", **ctx)


@bp.route("/reports/<int:report_id>/sacs.pdf")
def sacs_pdf(report_id):
    report = db.get_or_404(QuarterlyReport, report_id)
    return _serve_report_pdf(
        report,
        prefix="sacs",
        template="reports/sacs.html",
        context_fn=report_builder.prepare_sacs_context,
        css_files=["css/portal.css", "css/report-sacs.css"],
        kind="SACS",
    )


@bp.route("/reports/<int:report_id>/tcc.pdf")
def tcc_pdf(report_id):
    report = db.get_or_404(QuarterlyReport, report_id)
    return _serve_report_pdf(
        report,
        prefix="tcc",
        template="reports/tcc.html",
        context_fn=report_builder.prepare_tcc_context,
        css_files=["css/portal.css", "css/report-tcc.css"],
        kind="TCC",
    )


@bp.route("/reports")
def history():
    clients = Client.query.order_by(Client.household_name).all()

    q = QuarterlyReport.query.join(Client).order_by(QuarterlyReport.report_date.desc(), QuarterlyReport.id.desc())

    filter_client_id = request.args.get("client_id", type=int)
    if filter_client_id:
        q = q.filter(QuarterlyReport.client_id == filter_client_id)

    filter_quarter = (request.args.get("quarter") or "").strip()
    if filter_quarter:
        q = q.filter(QuarterlyReport.quarter_label.ilike(f"%{filter_quarter}%"))

    reports = q.all()
    return render_template(
        "reports/history.html",
        reports=reports,
        clients=clients,
        filter_client_id=filter_client_id,
        filter_quarter=filter_quarter,
        pdf_available=pdf_service.is_available(),
    )


# -- PDF helpers -----------------------------------------------------------

def _serve_report_pdf(report, *, prefix, template, context_fn, css_files, kind):
    """Render a report template through WeasyPrint and stream it as an
    application/pdf attachment. Serves a friendly fallback page when
    WeasyPrint can't load its native dependencies."""
    if not pdf_service.is_available():
        return render_template(
            "reports/_pdf_unavailable.html",
            report=report,
            kind=kind,
            detail=pdf_service.import_error_message(),
        ), 503

    ctx = context_fn(report)
    try:
        pdf_bytes = pdf_service.render_pdf(template, ctx, css_files=css_files)
    except Exception:
        current_app.logger.exception("PDF generation failed for %s report %s", kind, report.id)
        return render_template(
            "reports/_pdf_unavailable.html",
            report=report,
            kind=kind,
            detail="PDF generation encountered an error. Check server logs for the full traceback.",
        ), 500

    filename = pdf_service.build_filename(prefix, report.client.household_name, report.quarter_label)
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# -- helpers ---------------------------------------------------------------

def _render_new(client, form=None, errors=None):
    ctx = report_entry_service.build_entry_context(client)
    return render_template(
        "reports/new.html",
        client=client,
        groups=ctx["groups"],
        previous_report=ctx["previous_report"],
        previous_balances=ctx["previous_balances"],
        previous_label=ctx["previous_label"],
        form=form if form is not None else ctx["default_form"],
        errors=errors or {},
    )
