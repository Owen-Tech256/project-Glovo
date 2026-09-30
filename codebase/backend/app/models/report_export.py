"""One generated export run (SRS 9/12/13: "report exports", "CSV").
Generation in this phase is synchronous and small-scale (the underlying
analytics queries are the same bounded aggregate queries the dashboards
already run) - a row is created PROCESSING and flipped to COMPLETED/FAILED
in the same request, with the file written under the instance folder and
served back through an authorized download endpoint
(app/reports/routes.py), never as a static/public path. The status/timing
columns are still modeled as a real lifecycle so a future async worker is
a swap of *how* `status` transitions happen, not a schema change."""
import enum
import json

from app.extensions import db
from app.models.base import PublicIdMixin, TimestampMixin


class ReportExportStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ReportExport(db.Model, PublicIdMixin, TimestampMixin):
    __tablename__ = "report_exports"

    id = db.Column(db.Integer, primary_key=True)
    report_definition_id = db.Column(
        db.Integer, db.ForeignKey("report_definitions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Denormalized so an ad-hoc export (no saved ReportDefinition) still
    # records what kind of report it was.
    report_type = db.Column(db.String(25), nullable=False)
    requested_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    filters = db.Column(db.Text, nullable=True)  # JSON snapshot of the filters used
    file_reference = db.Column(db.String(500), nullable=True)
    row_count = db.Column(db.Integer, nullable=True)
    status = db.Column(
        db.Enum(ReportExportStatus, name="report_export_status", native_enum=False, length=15),
        nullable=False, default=ReportExportStatus.PENDING, index=True,
    )
    error_message = db.Column(db.String(500), nullable=True)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    requester = db.relationship("User")
    definition = db.relationship("ReportDefinition")

    def get_filters(self) -> dict:
        if not self.filters:
            return {}
        try:
            return json.loads(self.filters)
        except (TypeError, ValueError):
            return {}

    def to_public_dict(self) -> dict:
        return {
            "id": self.public_id,
            "report_definition_id": self.definition.public_id if self.definition else None,
            "report_type": self.report_type,
            "requested_by": self.requester.public_id if self.requester else None,
            "filters": self.get_filters(),
            "row_count": self.row_count,
            "status": self.status.value if isinstance(self.status, ReportExportStatus) else self.status,
            "error_message": self.error_message,
            "downloadable": self.status == ReportExportStatus.COMPLETED,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):  # pragma: no cover
        return f"<ReportExport {self.public_id} {self.report_type} {self.status}>"
