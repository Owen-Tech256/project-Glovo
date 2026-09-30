"""
The only provider adapter wired up in this phase (SRS Dependencies: "A
configurable payment/payout provider adapter" - no real gateway account
exists to integrate against, the same constraint Phase 3 documented for
its payment placeholder). Unlike that placeholder, every call here still
goes through the full, real Payment/PaymentTransaction/webhook/ledger
pipeline - only the "is this card actually good" decision is simulated,
deterministically, so the whole money layer is exercised and testable
without a live gateway account. See PHASE_5_NOTES.md.

Every operation is synchronous and succeeds unless deliberately told to
fail via a documented test-only sentinel, so tests can drive both the
happy path and every failure/retry path without any network access:
  - charge():  payment.method == "MOCK_DECLINE"        -> FAILED
  - refund():  refund.reason contains "MOCK_FAIL"        -> FAILED
  - payout():  payout.destination_reference contains
               "MOCK_FAIL"                                -> FAILED
"""
import hashlib
import hmac
import json
import secrets

from flask import current_app

from app.payments.providers.base import (
    PaymentProviderAdapter, ChargeResult, VerifyResult, RefundResult, PayoutResult,
)


class MockProviderAdapter(PaymentProviderAdapter):
    name = "mock"

    def _secret(self) -> bytes:
        return current_app.config.get("MOCK_PROVIDER_WEBHOOK_SECRET", "dev-webhook-secret-change-me").encode("utf-8")

    def charge(self, payment) -> ChargeResult:
        if payment.method == "MOCK_DECLINE":
            return ChargeResult(
                status="FAILED",
                provider_reference=f"mock_ch_{secrets.token_hex(12)}",
                external_event_id=f"evt_{secrets.token_hex(8)}",
                failure_reason="The card was declined (simulated).",
            )
        return ChargeResult(
            status="SUCCEEDED",
            provider_reference=f"mock_ch_{secrets.token_hex(12)}",
            external_event_id=f"evt_{secrets.token_hex(8)}",
        )

    def verify(self, payment) -> VerifyResult:
        # A real adapter would re-query the gateway by provider_reference.
        # The mock has no external state to diverge from what charge()
        # already decided, so it just re-affirms it - this still exercises
        # the full server-side verification code path (SRS 6).
        if payment.method == "MOCK_DECLINE":
            return VerifyResult(status="FAILED", provider_reference=payment.provider_reference,
                                 failure_reason="The card was declined (simulated).")
        return VerifyResult(status="SUCCEEDED", provider_reference=payment.provider_reference)

    def refund(self, refund, payment) -> RefundResult:
        if refund.reason and "MOCK_FAIL" in refund.reason:
            return RefundResult(
                status="FAILED",
                provider_reference=f"mock_rf_{secrets.token_hex(12)}",
                external_event_id=f"evt_{secrets.token_hex(8)}",
                failure_reason="The refund was declined by the provider (simulated).",
            )
        return RefundResult(
            status="SUCCEEDED",
            provider_reference=f"mock_rf_{secrets.token_hex(12)}",
            external_event_id=f"evt_{secrets.token_hex(8)}",
        )

    def payout(self, payout) -> PayoutResult:
        if payout.destination_reference and "MOCK_FAIL" in payout.destination_reference:
            return PayoutResult(
                status="FAILED",
                provider_reference=f"mock_po_{secrets.token_hex(12)}",
                failure_reason="The payout destination rejected the transfer (simulated).",
            )
        return PayoutResult(status="PAID", provider_reference=f"mock_po_{secrets.token_hex(12)}")

    def verify_webhook_signature(self, raw_body: bytes, signature_header: str | None) -> bool:
        if not signature_header:
            return False
        expected = hmac.new(self._secret(), raw_body, hashlib.sha256).hexdigest()
        try:
            return hmac.compare_digest(expected, signature_header)
        except TypeError:
            return False

    @staticmethod
    def sign(payload: dict, secret: bytes) -> str:
        """Test/ops convenience: compute the signature this adapter would
        require for a given payload, mirroring how a real gateway's own
        test-mode tooling lets you build a valid signed webhook call."""
        raw_body = json.dumps(payload, sort_keys=True).encode("utf-8")
        return hmac.new(secret, raw_body, hashlib.sha256).hexdigest()
