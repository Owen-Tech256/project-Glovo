from app.extensions import db
from app.models.base import _utcnow


class OrderAddressSnapshot(db.Model):
    """Immutable copy of the delivery address at order-creation time.

    Deliberately not `PublicIdMixin` / `TimestampMixin`-based: it is a
    write-once child of exactly one order (1:1), never listed or fetched on
    its own, and never updated after creation - editing or deleting the
    customer's saved `CustomerAddress` later must never change what an
    already-placed order shows.
    """

    __tablename__ = "order_address_snapshots"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(
        db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    source_address_id = db.Column(
        db.Integer, db.ForeignKey("customer_addresses.id", ondelete="SET NULL"), nullable=True
    )

    recipient_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(32), nullable=False)
    address_line1 = db.Column(db.String(255), nullable=False)
    address_line2 = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100), nullable=True)
    postal_code = db.Column(db.String(20), nullable=True)
    country = db.Column(db.String(100), nullable=False)
    latitude = db.Column(db.Numeric(9, 6), nullable=False)
    longitude = db.Column(db.Numeric(9, 6), nullable=False)
    delivery_instructions = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    def to_public_dict(self) -> dict:
        return {
            "recipient_name": self.recipient_name,
            "phone": self.phone,
            "address_line1": self.address_line1,
            "address_line2": self.address_line2,
            "city": self.city,
            "state": self.state,
            "postal_code": self.postal_code,
            "country": self.country,
            "latitude": float(self.latitude) if self.latitude is not None else None,
            "longitude": float(self.longitude) if self.longitude is not None else None,
            "delivery_instructions": self.delivery_instructions,
        }

    @classmethod
    def from_customer_address(cls, order_id: int, address) -> "OrderAddressSnapshot":
        return cls(
            order_id=order_id,
            source_address_id=address.id,
            recipient_name=address.recipient_name,
            phone=address.phone,
            address_line1=address.address_line1,
            address_line2=address.address_line2,
            city=address.city,
            state=address.state,
            postal_code=address.postal_code,
            country=address.country,
            latitude=address.latitude,
            longitude=address.longitude,
            delivery_instructions=address.delivery_instructions,
        )

    def __repr__(self):  # pragma: no cover
        return f"<OrderAddressSnapshot order_id={self.order_id}>"
