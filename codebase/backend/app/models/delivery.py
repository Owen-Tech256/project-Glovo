import enum

from app.extensions import db
from app.models.base import PublicIdMixin, TimestampMixin


class DeliveryStatus(str, enum.Enum):
    CREATED = "CREATED"
    SEARCHING = "SEARCHING"
    OFFERED = "OFFERED"
    ASSIGNED = "ASSIGNED"
    PICKED_UP = "PICKED_UP"
    DELIVERING = "DELIVERING"
    DELIVERED = "DELIVERED"
    # Not named in the SRS's headline state list (CREATED -> ... ->
    # DELIVERED), but required by "Support controlled reassignment" and
    # "Admin: ... authorized reassignment/intervention" (SRS 8-9): a
    # delivery that exhausts every dispatch candidate, or that an admin
    # deliberately calls off, needs a terminal state distinct from
    # DELIVERED. See PHASE_4_NOTES.md assumption #1.
    CANCELLED = "CANCELLED"


class Delivery(db.Model, PublicIdMixin, TimestampMixin):
    """The logistics counterpart of one Phase 3 order, created the moment a
    vendor marks that order READY (SRS 8: "Create exactly one active
    delivery for an eligible READY order"). `order_id` is unique - this
    phase has no delivery-retry-with-a-new-row workflow; a cancelled
    delivery is not recreated, and reassignment reuses this same row (see
    app/logistics/dispatch_service.py).

    `pickup_*`/`destination_*` are snapshots taken from the branch and the
    order's address snapshot at creation time, mirroring the
    OrderAddressSnapshot pattern from Phase 3: dispatch ranking and
    tracking must never silently change if a branch's address or a
    customer's saved address is edited after the delivery already exists.
    """

    __tablename__ = "deliveries"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(
        db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False, index=True)
    rider_id = db.Column(db.Integer, db.ForeignKey("riders.id", ondelete="SET NULL"), nullable=True, index=True)

    status = db.Column(
        db.Enum(DeliveryStatus, name="delivery_status", native_enum=False, length=20),
        nullable=False,
        default=DeliveryStatus.CREATED,
        index=True,
    )

    pickup_latitude = db.Column(db.Numeric(9, 6), nullable=False)
    pickup_longitude = db.Column(db.Numeric(9, 6), nullable=False)
    destination_latitude = db.Column(db.Numeric(9, 6), nullable=False)
    destination_longitude = db.Column(db.Numeric(9, 6), nullable=False)

    assigned_at = db.Column(db.DateTime(timezone=True), nullable=True)
    picked_up_at = db.Column(db.DateTime(timezone=True), nullable=True)
    delivered_at = db.Column(db.DateTime(timezone=True), nullable=True)
    cancelled_at = db.Column(db.DateTime(timezone=True), nullable=True)
    cancellation_reason = db.Column(db.String(500), nullable=True)

    order = db.relationship("Order", backref=db.backref("delivery", uselist=False))
    branch = db.relationship("Branch")
    rider = db.relationship("Rider")

    assignments = db.relationship(
        "DeliveryAssignment", backref="delivery", lazy="dynamic", cascade="all, delete-orphan",
        order_by="DeliveryAssignment.offered_at.desc()",
    )
    status_history = db.relationship(
        "DeliveryStatusHistory", backref="delivery", lazy="dynamic", cascade="all, delete-orphan",
        order_by="DeliveryStatusHistory.created_at",
    )
    locations = db.relationship(
        "DeliveryLocation", backref="delivery", lazy="dynamic", cascade="all, delete-orphan",
        order_by="DeliveryLocation.recorded_at.desc()",
    )

    __table_args__ = (
        db.CheckConstraint("pickup_latitude >= -90 AND pickup_latitude <= 90", name="ck_deliveries_pickup_lat_range"),
        db.CheckConstraint(
            "pickup_longitude >= -180 AND pickup_longitude <= 180", name="ck_deliveries_pickup_lng_range"
        ),
        db.CheckConstraint(
            "destination_latitude >= -90 AND destination_latitude <= 90", name="ck_deliveries_dest_lat_range"
        ),
        db.CheckConstraint(
            "destination_longitude >= -180 AND destination_longitude <= 180", name="ck_deliveries_dest_lng_range"
        ),
        db.Index("ix_deliveries_branch_status", "branch_id", "status"),
        db.Index("ix_deliveries_rider_status", "rider_id", "status"),
    )

    def to_public_dict(self, include_order: bool = True) -> dict:
        data = {
            "id": self.public_id,
            "order_id": self.order.public_id if self.order else None,
            "order_number": self.order.public_order_number if self.order else None,
            "branch_id": self.branch.public_id if self.branch else None,
            "branch_name": self.branch.name if self.branch else None,
            "rider_id": self.rider.public_id if self.rider else None,
            "rider_name": self.rider.user.full_name if self.rider and self.rider.user else None,
            "status": self.status.value if isinstance(self.status, DeliveryStatus) else self.status,
            "pickup_latitude": float(self.pickup_latitude) if self.pickup_latitude is not None else None,
            "pickup_longitude": float(self.pickup_longitude) if self.pickup_longitude is not None else None,
            "destination_latitude": float(self.destination_latitude)
            if self.destination_latitude is not None else None,
            "destination_longitude": float(self.destination_longitude)
            if self.destination_longitude is not None else None,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "picked_up_at": self.picked_up_at.isoformat() if self.picked_up_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "cancellation_reason": self.cancellation_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_order and self.order:
            data["order_status"] = self.order.status.value if hasattr(self.order.status, "value") else self.order.status
        return data

    def __repr__(self):  # pragma: no cover
        return f"<Delivery {self.public_id} order_id={self.order_id} status={self.status}>"
