"""
Report definitions and CSV exports (SRS 9/12/13, implementation prompt 5:
"Implement authorized report export"). Generation is synchronous: the
underlying data is the same bounded aggregate/listing queries the
dashboards already run, so there is no need for a background worker in
this phase (a documented scope reduction - see PHASE_7_NOTES.md). Each
`ReportExport` still models a real PENDING -> PROCESSING -> COMPLETED/
FAILED lifecycle so swapping in an async worker later is a change in how
that transition happens, not a schema change.

Files are written under the app's instance folder
(`<instance_path>/report_exports/<export public_id>.csv`) and only ever
served back through `app/reports/routes.py`'s authorized download
endpoint - never as a static/public path (SRS 14: "Secure attachments and
report data").
"""
import csv
import io
import json
import os

from flask import current_app

from app.extensions import db
from app.common.errors import NotFoundError, ValidationAppError
from app.models.report_definition import ReportDefinition, ReportType
from app.models.report_export import ReportExport, ReportExportStatus
from app.analytics import service as analytics_service


def _export_dir() -> str:
    path = os.path.join(current_app.instance_path, "report_exports")
    os.makedirs(path, exist_ok=True)
    return path


def _rows_for_report(report_type: ReportType, date_from: str | None, date_to: str | None,
                      filters: dict) -> tuple[list[str], list[list[str]]]:
    """Returns (header_row, data_rows) for the given report type. Orders
    gets a genuine row-per-order listing (the kind of raw export SRS 9's
    "Exports such as CSV" is really for); every other type exports the
    same aggregate breakdown its dashboard shows, one row per dimension
    value, since that *is* the meaningful unit for those domains."""
    if report_type == ReportType.ORDERS:
        from app.models.order import Order

        start, end = analytics_service.resolve_range(date_from, date_to)
        query = Order.query.filter(Order.created_at >= start, Order.created_at < end)
        if filters.get("status"):
            query = query.filter(Order.status == filters["status"])
        orders = query.order_by(Order.created_at.asc()).limit(10000).all()
        header = ["order_number", "status", "subtotal", "fees", "discount_total", "total", "created_at"]
        rows = [
            [o.public_order_number, o.status.value, str(o.subtotal), str(o.fees), str(o.discount_total), str(o.total),
             o.created_at.isoformat()]
            for o in orders
        ]
        return header, rows

    if report_type == ReportType.FINANCE:
        data = analytics_service.finance_metrics(date_from, date_to)
        return list(data.keys()), [[str(v) for v in data.values()]]

    if report_type == ReportType.VENDORS:
        data = analytics_service.vendor_metrics(date_from, date_to, vendor_public_id=filters.get("vendor_id"))
        vendors = data["vendors"]
        header = ["vendor_id", "vendor_name", "order_count", "gross_sales", "discounts", "refunds", "net_sales", "average_order_value"]
        rows = [[v[k] for k in header] for v in vendors]
        return header, rows

    if report_type == ReportType.RIDERS:
        data = analytics_service.rider_metrics(date_from, date_to, rider_public_id=filters.get("rider_id"))
        riders = data["riders"]
        header = ["rider_id", "rating_average", "completed_deliveries", "offers_received", "acceptance_rate", "rejection_rate", "earnings"]
        rows = [[str(r[k]) for k in header] for r in riders]
        return header, rows

    if report_type == ReportType.DELIVERY:
        data = analytics_service.delivery_metrics(date_from, date_to)
        return list(data.keys()), [[str(v) for v in data.values()]]

    if report_type == ReportType.CUSTOMERS:
        data = analytics_service.customer_metrics(date_from, date_to)
        return list(data.keys()), [[str(v) for v in data.values()]]

    if report_type == ReportType.PROMOTIONS_ADS:
        data = analytics_service.promotion_ad_metrics(date_from, date_to)
        return list(data.keys()), [[str(v) for v in data.values()]]

    # SUPPORT_DISPUTES: nested dict - flatten to one row per section.
    data = analytics_service.support_dispute_metrics(date_from, date_to)
    header = ["section", "total", "backlog", "avg_resolution_seconds", "breakdown"]
    rows = []
    for section in ("tickets", "disputes"):
        s = data[section]
        rows.append([section, str(s["total"]), str(s["backlog"]), str(s["avg_resolution_seconds"]),
                     json.dumps(s.get("by_status", {}))])
    return header, rows


def request_export(actor, report_type_str: str | None, report_definition_public_id: str | None,
                    date_from: str | None, date_to: str | None, filters: dict) -> ReportExport:
    definition = None
    if report_definition_public_id:
        definition = ReportDefinition.query.filter_by(public_id=report_definition_public_id).first()
        if definition is None:
            raise NotFoundError("Report definition not found.")
        report_type = definition.report_type
        merged_filters = {**definition.get_configuration(), **filters}
    elif report_type_str:
        report_type = ReportType(report_type_str)
        merged_filters = filters
    else:
        raise ValidationAppError("Either report_type or report_definition_id is required.", code="REPORT_TYPE_REQUIRED")

    export = ReportExport(
        report_definition_id=definition.id if definition else None,
        report_type=report_type.value,
        requested_by=actor.id,
        filters=json.dumps({"date_from": date_from, "date_to": date_to, **merged_filters}, default=str),
        status=ReportExportStatus.PROCESSING,
    )
    db.session.add(export)
    db.session.commit()

    try:
        header, rows = _rows_for_report(report_type, date_from, date_to, merged_filters)
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(header)
        writer.writerows(rows)

        filename = f"{export.public_id}.csv"
        with open(os.path.join(_export_dir(), filename), "w", newline="") as fh:
            fh.write(buffer.getvalue())

        export.file_reference = filename
        export.row_count = len(rows)
        export.status = ReportExportStatus.COMPLETED
        from app.models.base import _utcnow

        export.completed_at = _utcnow()
    except Exception as exc:  # noqa: BLE001
        export.status = ReportExportStatus.FAILED
        export.error_message = str(exc)[:500]
    db.session.commit()
    return export


def get_export_or_404(export_public_id: str) -> ReportExport:
    export = ReportExport.query.filter_by(public_id=export_public_id).first()
    if export is None:
        raise NotFoundError("Report export not found.")
    return export


def export_file_path(export: ReportExport) -> str:
    if export.status != ReportExportStatus.COMPLETED or not export.file_reference:
        raise ValidationAppError("This export is not ready for download.", code="EXPORT_NOT_READY")
    return os.path.join(_export_dir(), export.file_reference)


def list_exports(page: int = 1, per_page: int = 20):
    return ReportExport.query.order_by(ReportExport.created_at.desc()).paginate(
        page=max(page, 1), per_page=max(min(per_page, 100), 1), error_out=False
    )


# --- Report definitions --------------------------------------------------

def create_definition(actor, name: str, report_type: str, configuration: dict, access_level: str) -> ReportDefinition:
    definition = ReportDefinition(
        name=name, report_type=ReportType(report_type), configuration=json.dumps(configuration, default=str),
        access_level=access_level, created_by=actor.id,
    )
    db.session.add(definition)
    db.session.commit()
    return definition


def list_definitions() -> list[ReportDefinition]:
    return ReportDefinition.query.order_by(ReportDefinition.created_at.desc()).all()
