import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowLeft, MapPin, Tag, X } from "lucide-react";
import { DashboardLayout } from "../../../layouts/DashboardLayout";
import { Card, CardBody } from "../../../components/ui/Card";
import { Button } from "../../../components/ui/Button";
import { Select } from "../../../components/ui/Select";
import { Input } from "../../../components/ui/Input";
import { Alert } from "../../../components/ui/Alert";
import { EmptyState } from "../../../components/ui/EmptyState";
import { useToast } from "../../../context/ToastContext";
import { addressService } from "../../../services/addressService";
import { orderService } from "../../../services/orderService";
import { paymentService } from "../../../services/paymentService";
import { cartService } from "../../../services/cartService";
import { extractApiErrorMessage } from "../../../services/apiClient";
import type { CustomerAddress } from "../../../types/catalog";
import type { CheckoutSummary } from "../../../types/order";
import { SkeletonBlock } from "../../../components/ui/Skeleton";

const ISSUE_LABELS: Record<string, string> = {
  BRANCH_UNAVAILABLE: "This branch is not currently accepting orders.",
  PRODUCT_UNAVAILABLE: "One of your items is no longer available. Update your cart to continue.",
  CART_EMPTY: "Your cart is empty.",
  ADDRESS_OUT_OF_RANGE: "This address is outside the branch's delivery area. Choose a different address.",
};

function makeIdempotencyKey(): string {
  return typeof crypto !== "undefined" && crypto.randomUUID
    ? crypto.randomUUID()
    : `order-${Date.now()}-${Math.random()}`;
}

export function CheckoutPage() {
  const [searchParams] = useSearchParams();
  const branchId = searchParams.get("branch");
  const navigate = useNavigate();
  const { showError, showSuccess } = useToast();

  const [addresses, setAddresses] = useState<CustomerAddress[]>([]);
  const [addressId, setAddressId] = useState<string>("");
  const [summary, setSummary] = useState<CheckoutSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [placingOrder, setPlacingOrder] = useState(false);
  // Per-checkout-attempt key so a retried "Place order" click (e.g. after a
  // transient network error) replays the same order instead of creating a
  // second one. Regenerated whenever the branch changes, since the backend
  // scopes replay only by (customer, key) - reusing a key across two
  // different branches would incorrectly return the first branch's order.
  const [idempotencyKey, setIdempotencyKey] = useState(makeIdempotencyKey);
  const [promoCode, setPromoCode] = useState("");
  const [applyingPromo, setApplyingPromo] = useState(false);

  useEffect(() => {
    setIdempotencyKey(makeIdempotencyKey());
  }, [branchId]);

  useEffect(() => {
    addressService
      .list()
      .then((list) => {
        setAddresses(list);
        const preferred = list.find((a) => a.is_default) ?? list[0];
        if (preferred) setAddressId(preferred.id);
      })
      .catch(() => showError("Could not load your addresses."))
      .finally(() => setLoading(false));
  }, [showError]);

  function loadSummary() {
    if (!branchId || !addressId) {
      setSummary(null);
      return;
    }
    orderService
      .getCheckoutSummary(branchId, addressId)
      .then(setSummary)
      .catch(() => showError("Could not load your order summary."));
  }

  useEffect(loadSummary, [branchId, addressId, showError]);

  async function handleApplyPromo() {
    if (!branchId || !promoCode.trim()) return;
    setApplyingPromo(true);
    try {
      await cartService.applyPromotion(branchId, promoCode.trim());
      setPromoCode("");
      loadSummary();
      showSuccess("Promotion applied.");
    } catch (error) {
      showError(extractApiErrorMessage(error, "That code could not be applied."));
    } finally {
      setApplyingPromo(false);
    }
  }

  async function handleRemovePromo() {
    if (!branchId) return;
    try {
      await cartService.removePromotion(branchId);
      loadSummary();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not remove the promotion."));
    }
  }

  async function handlePlaceOrder() {
    if (!branchId || !addressId) return;
    setPlacingOrder(true);
    try {
      const order = await orderService.createOrder(branchId, addressId, idempotencyKey);
      // Phase 5: an order no longer auto-confirms payment - pay for it as
      // part of the same "Place order" click (this mock gateway always
      // resolves synchronously). A failed charge still leaves the order
      // created, so send the customer to the order page either way; it
      // shows the payment outcome and offers a retry.
      try {
        await paymentService.createPayment(order.id, "CARD", idempotencyKey);
        showSuccess("Order placed and paid.");
      } catch {
        showError("Order placed, but the payment did not go through. You can retry it from the order page.");
      }
      navigate(`/customer/dashboard/orders/${order.id}`);
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not place your order."));
    } finally {
      setPlacingOrder(false);
    }
  }

  if (!branchId) {
    return (
      <DashboardLayout>
        <EmptyState icon={<MapPin className="h-5 w-5" />} title="No branch selected" description="Go back to your cart and try again." />
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-6 max-w-2xl">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink">Checkout</h1>
          <p className="text-ink-soft mt-1">Confirm your delivery address and review your order.</p>
        </div>

        {loading ? (
          <SkeletonBlock className="h-64" />
        ) : addresses.length === 0 ? (
          <EmptyState
            icon={<MapPin className="h-5 w-5" />}
            title="No delivery address yet"
            description="Add a delivery address before you can check out."
          />
        ) : (
          <>
            <Card>
              <CardBody className="space-y-4">
                <Select label="Delivery address" value={addressId} onChange={(e) => setAddressId(e.target.value)}>
                  {addresses.map((address) => (
                    <option key={address.id} value={address.id}>
                      {address.label} - {address.address_line1}, {address.city}
                    </option>
                  ))}
                </Select>
                <Link to="/customer/dashboard/addresses" className="text-sm text-primary hover:underline">
                  Manage addresses
                </Link>
              </CardBody>
            </Card>

            {summary && (
              <Card>
                <CardBody className="space-y-4">
                  <p className="font-display text-lg font-semibold text-ink">{summary.branch.name}</p>

                  {!summary.is_valid && (
                    <Alert tone="danger">
                      <div className="space-y-1">
                        {summary.issues.map((issue, index) => (
                          <p key={index}>{ISSUE_LABELS[issue.reason] ?? "This order has an issue."}</p>
                        ))}
                      </div>
                    </Alert>
                  )}

                  <div className="space-y-2 border-t border-line pt-4">
                    {summary.applied_promotion ? (
                      <div className="flex items-center justify-between rounded-lg bg-primary/5 px-3 py-2 text-sm">
                        <span className="flex items-center gap-1.5 text-ink">
                          <Tag className="h-3.5 w-3.5 text-primary" />
                          {summary.applied_promotion.code ?? summary.applied_promotion.name}
                        </span>
                        <button type="button" onClick={handleRemovePromo} className="text-ink-soft hover:text-ink">
                          <X className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    ) : (
                      <div className="flex gap-2 items-end">
                        <Input
                          label="Promo code"
                          placeholder="e.g. SAVE10"
                          value={promoCode}
                          onChange={(e) => setPromoCode(e.target.value)}
                          className="flex-1"
                        />
                        <Button variant="secondary" isLoading={applyingPromo} onClick={handleApplyPromo} disabled={!promoCode.trim()}>
                          Apply
                        </Button>
                      </div>
                    )}
                    {summary.promotion_issue && (
                      <p className="text-xs text-danger">This promotion no longer applies to your cart.</p>
                    )}
                  </div>

                  <div className="space-y-2 border-t border-line pt-4 text-sm">
                    <div className="flex justify-between text-ink-soft">
                      <span>Subtotal</span>
                      <span>${summary.subtotal}</span>
                    </div>
                    {Number(summary.discount_total) > 0 && (
                      <div className="flex justify-between text-primary">
                        <span>Discount</span>
                        <span>-${summary.discount_total}</span>
                      </div>
                    )}
                    <div className="flex justify-between text-ink-soft">
                      <span>Delivery fee</span>
                      <span>${summary.fees}</span>
                    </div>
                    <div className="flex justify-between font-display text-base font-semibold text-ink pt-2 border-t border-line">
                      <span>Total</span>
                      <span>${summary.total}</span>
                    </div>
                  </div>

                  <Button fullWidth isLoading={placingOrder} disabled={!summary.is_valid} onClick={handlePlaceOrder}>
                    Place order &amp; pay
                  </Button>
                </CardBody>
              </Card>
            )}
          </>
        )}

        <Link
          to={`/customer/dashboard/cart?branch=${branchId}`}
          className="inline-flex items-center gap-1.5 text-sm text-ink-soft hover:text-ink"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to cart
        </Link>
      </div>
    </DashboardLayout>
  );
}
