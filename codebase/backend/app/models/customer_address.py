from app.extensions import db
from app.models.base import PublicIdMixin, TimestampMixin


class CustomerAddress(db.Model, PublicIdMixin, TimestampMixin):
    __tablename__ = "customer_addresses"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    label = db.Column(db.String(100), nullable=False)
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
    is_default = db.Column(db.Boolean, nullable=False, default=False, index=True)

    owner = db.relationship("User", backref=db.backref("addresses", lazy="dynamic", cascade="all, delete-orphan"))

    __table_args__ = (
        db.CheckConstraint("latitude >= -90 AND latitude <= 90", name="ck_customer_addresses_latitude_range"),
        db.CheckConstraint("longitude >= -180 AND longitude <= 180", name="ck_customer_addresses_longitude_range"),
        db.Index("ix_customer_addresses_user_default", "user_id", "is_default"),
    )

    def to_public_dict(self) -> dict:
        return {
            "id": self.public_id,
            "label": self.label,
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
            "is_default": self.is_default,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):  # pragma: no cover
        return f"<CustomerAddress {self.public_id} user_id={self.user_id}>"
