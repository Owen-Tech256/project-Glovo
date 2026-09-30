"""Saved, reusable report configurations (SRS 9/12). Running a definition
or requesting an ad-hoc export both produce a ReportExport row -
`report_export.py` is the actual generated artifact; this is just the
reusable recipe."""
import enum
import json

from app.extensions import db
from app.models.base import PublicIdMixin, TimestampMixin


class ReportType(str, enum.Enum):
    ORDERS = "ORDERS"
    FINANCE = "FINANCE"
    VENDORS = "VENDORS"
    RIDERS = "RIDERS"
    DELIVERY = "DELIVERY"
    CUSTOMERS = "CUSTOMERS"
    PROMOTIONS_ADS = "PROMOTIONS_ADS"
    SUPPORT_DISPUTES = "SUPPORT_DISPUTES"


class ReportDefinition(db.Model, PublicIdMixin, TimestampMixin):
    __tablename__ = "report_definitions"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    report_type = db.Column(db.Enum(ReportType, name="report_type", native_enum=False, length=25), nullable=False)
    configuration = db.Column(db.Text, nullable=True)  # JSON: default filters (date range, status, etc.)
    # A required admin_permissions.key: only staff holding this permission
    # (or a SUPER_ADMIN) may run or export this definition.
    access_level = db.Column(db.String(80), nullable=False, default="analytics.view")
    created_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    creator = db.relationship("User")

    def get_configuration(self) -> dict:
        if not self.configuration:
            return {}
        try:
            return json.loads(self.configuration)
        except (TypeError, ValueError):
            return {}

    def to_public_dict(self) -> dict:
        return {
            "id": self.public_id,
            "name": self.name,
            "report_type": self.report_type.value if isinstance(self.report_type, ReportType) else self.report_type,
            "configuration": self.get_configuration(),
            "access_level": self.access_level,
            "created_by": self.creator.public_id if self.creator else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):  # pragma: no cover
        return f"<ReportDefinition {self.name} {self.report_type}>"
