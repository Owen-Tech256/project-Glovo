"""
The provider adapter interface (SRS 6: "Use a provider adapter so business
logic is not tied to one gateway"). Every method returns a small,
provider-agnostic result object; app/payments/payment_service.py,
refund_service.py and vendor_finance_service.py only ever talk to these
shapes, never to a specific gateway's SDK/response format. Swapping in a
real gateway later means writing one new adapter class and pointing
DEFAULT_PAYMENT_PROVIDER (app/config.py) at it - no service-layer changes.
"""
from dataclasses import dataclass


@dataclass
class ChargeResult:
    status: str  # "SUCCEEDED" | "PENDING" | "FAILED"
    provider_reference: str
    external_event_id: str | None = None
    failure_reason: str | None = None


@dataclass
class VerifyResult:
    status: str  # "SUCCEEDED" | "PENDING" | "FAILED"
    provider_reference: str | None = None
    failure_reason: str | None = None


@dataclass
class RefundResult:
    status: str  # "SUCCEEDED" | "PENDING" | "FAILED"
    provider_reference: str
    external_event_id: str | None = None
    failure_reason: str | None = None


@dataclass
class PayoutResult:
    status: str  # "PAID" | "PENDING" | "FAILED"
    provider_reference: str
    failure_reason: str | None = None


class PaymentProviderAdapter:
    """Abstract base. Every provider adapter (mock, or a future real
    gateway) implements this surface."""

    name = "base"

    def charge(self, payment) -> ChargeResult:
        raise NotImplementedError

    def verify(self, payment) -> VerifyResult:
        raise NotImplementedError

    def refund(self, refund, payment) -> RefundResult:
        raise NotImplementedError

    def payout(self, payout) -> PayoutResult:
        raise NotImplementedError

    def verify_webhook_signature(self, raw_body: bytes, signature_header: str | None) -> bool:
        raise NotImplementedError
