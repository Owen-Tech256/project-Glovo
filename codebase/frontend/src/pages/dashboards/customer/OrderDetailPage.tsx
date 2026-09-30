import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, MapPin, Receipt, Bike, CreditCard, RotateCcw, Star, MessageSquare } from "lucide-react";
import { DashboardLayout } from "../../../layouts/DashboardLayout";
import { Card, CardBody, CardHeader } from "../../../components/ui/Card";
import { Button } from "../../../components/ui/Button";
import { Modal } from "../../../components/ui/Modal";
import { Input } from "../../../components/ui/Input";
import { Textarea } from "../../../components/ui/Textarea";
import { StatusBadge } from "../../../components/ui/Badge";
import { Alert } from "../../../components/ui/Alert";
import { EmptyState } from "../../../components/ui/EmptyState";
import { useToast } from "../../../context/ToastContext";
import { orderService } from "../../../services/orderService";
import { logisticsService } from "../../../services/logisticsService";
import { paymentService } from "../../../services/paymentService";
import { reviewService } from "../../../services/reviewService";
import { extractApiErrorMessage } from "../../../services/apiClient";
import { CANCELLABLE_STATUSES } from "../../../types/order";
import type { Order, OrderStatusHistoryEntry } from "../../../types/order";
import type { DeliveryTracking } from "../../../types/logistics";
import type { Payment, Refund } from "../../../types/payments";
import type { ReviewableTarget } from "../../../types/growth";
import { SkeletonBlock } from "../../../components/ui/Skeleton";

function StarPicker({ value, onChange }: { value: number; onChange: (rating: number) => void }) {
  return (
    <div className="flex items-center gap-1">
      {[1, 2, 3, 4, 5].map((star) => (
        <button key={star} type="button" onClick={() => onChange(star)} className="p-0.5" aria-label={`${star} stars`}>
          <Star className={`h-5 w-5 ${star <= value ? "fill-primary text-primary" : "text-line-strong"}`} />
        </button>
      ))}
    </div>
  );
}

export function OrderDetailPage() {
  const { orderId } = useParams<{ orderId: string }>();
  const { showError, showSuccess } = useToast();
  const [order, setOrder] = useState<Order | null>(null);
  const [history, setHistory] = useState<OrderStatusHistoryEntry[]>([]);
  const [tracking, setTracking] = useState<DeliveryTracking | null>(null);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [refunds, setRefunds] = useState<Refund[]>([]);
  const [loading, setLoading] = useState(true);
  const [cancelModalOpen, setCancelModalOpen] = useState(false);
  const [cancelReason, setCancelReason] = useState("");
  const [cancelling, setCancelling] = useState(false);
  const [payingAgain, setPayingAgain] = useState(false);
  const [refundModalOpen, setRefundModalOpen] = useState(false);
  const [refundAmount, setRefundAmount] = useState("");
  const [refundReason, setRefundReason] = useState("");
  const [requestingRefund, setRequestingRefund] = useState(false);
  const [reviewable, setReviewable] = useState<ReviewableTarget[]>([]);
  const [reviewDrafts, setReviewDrafts] = useState<Record<string, { rating: number; body: string }>>({});
  const [submittingReview, setSubmittingReview] = useState<string | null>(null);

  const load = useCallback(() => {
    if (!orderId) return;
    setLoading(true);
    Promise.all([orderService.getMyOrder(orderId), orderService.getMyOrderStatusHistory(orderId)])
      .then(([o, h]) => {
        setOrder(o);
        setHistory(h);
      })
      .catch(() => showError("Could not load this order."))
      .finally(() => setLoading(false));
    // A delivery only exists once the vendor marks the order READY - a 404
    // here just means there's nothing to show yet, not an error.
    logisticsService
      .getOrderDelivery(orderId)
      .then(setTracking)
      .catch(() => setTracking(null));
    paymentService
      .listOrderPayments(orderId)
      .then(setPayments)
      .catch(() => setPayments([]));
    paymentService
      .listOrderRefunds(orderId)
      .then(setRefunds)
      .catch(() => setRefunds([]));
    reviewService
      .getReviewableTargets(orderId)
      .then(setReviewable)
      .catch(() => setReviewable([]));
  }, [orderId, showError]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleCancel() {
    if (!orderId) return;
    setCancelling(true);
    try {
      await orderService.cancelOrder(orderId, cancelReason || undefined);
      showSuccess("Order cancelled.");
      setCancelModalOpen(false);
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not cancel this order."));
    } finally {
      setCancelling(false);
    }
  }

  async function handlePayAgain() {
    if (!orderId) return;
    setPayingAgain(true);
    try {
      await paymentService.createPayment(orderId, "CARD");
      showSuccess("Payment submitted.");
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "The payment did not go through."));
    } finally {
      setPayingAgain(false);
    }
  }

  async function handleRequestRefund() {
    if (!orderId) return;
    setRequestingRefund(true);
    try {
      await paymentService.requestRefund(orderId, refundReason, refundAmount || undefined);
      showSuccess("Refund requested.");
      setRefundModalOpen(false);
      setRefundAmount("");
      setRefundReason("");
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not request a refund."));
    } finally {
      setRequestingRefund(false);
    }
  }

  async function handleSubmitReview(target: ReviewableTarget) {
    if (!orderId) return;
    const draft = reviewDrafts[target.target_id] ?? { rating: 5, body: "" };
    setSubmittingReview(target.target_id);
    try {
      await reviewService.submitReview(orderId, target.target_type, target.target_id, draft.rating, draft.body || undefined);
      showSuccess("Review submitted.");
      reviewService.getReviewableTargets(orderId).then(setReviewable);
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not submit your review."));
    } finally {
      setSubmittingReview(null);
    }
  }

  const TARGET_LABELS: Record<string, string> = { VENDOR: "the vendor", RIDER: "your rider", PRODUCT: "" };

  const latestPayment = payments[0] ?? null;
  const hasSucceededPayment = payments.some((p) => p.status === "SUCCEEDED" || p.status === "PARTIALLY_REFUNDED");
  const totalRefunded = refunds
    .filter((r) => r.status === "SUCCEEDED")
    .reduce((sum, r) => sum + Number(r.amount), 0);
  const refundableRemaining = order ? Number(order.total) - totalRefunded : 0;
  const hasOpenRefundRequest = refunds.some((r) => r.status === "REQUESTED" || r.status === "APPROVED" || r.status === "PROCESSING");
  const canRequestRefund = hasSucceededPayment && refundableRemaining > 0 && !hasOpenRefundRequest;

  return (
    <DashboardLayout>
      <div className="space-y-6 max-w-2xl">
        <Link to="/customer/dashboard/orders" className="inline-flex items-center gap-1.5 text-sm text-ink-soft hover:text-ink">
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to orders
        </Link>

        {loading ? (
          <SkeletonBlock className="h-64" />
        ) : !order ? (
          <EmptyState icon={<Receipt className="h-5 w-5" />} title="Order not found" description="This order is no longer available." />
        ) : (
          <>
            <div className="flex items-start justify-between gap-4">
              <div>
                <h1 className="font-display text-2xl font-semibold text-ink">{order.order_number}</h1>
                <p className="text-ink-soft mt-1">
                  {order.vendor_name ? `${order.vendor_name} - ` : ""}
                  {order.branch_name}
                </p>
              </div>
              <StatusBadge status={order.status} />
            </div>

            {order.status === "PENDING_PAYMENT" && (
              <Alert tone={latestPayment?.status === "FAILED" ? "danger" : "info"}>
                <div className="flex items-center justify-between gap-3">
                  <span>
                    {latestPayment?.status === "FAILED"
                      ? `Your last payment attempt was declined${latestPayment.failure_reason ? `: ${latestPayment.failure_reason}` : "."}`
                      : "This order is awaiting payment."}
                  </span>
                  <Button size="sm" isLoading={payingAgain} onClick={handlePayAgain}>
                    Pay now
                  </Button>
                </div>
              </Alert>
            )}

            <Card>
              <CardHeader>
                <p className="font-medium text-ink">Items</p>
              </CardHeader>
              <CardBody className="space-y-3">
                {order.items?.map((item) => (
                  <div key={item.id} className="flex items-center justify-between text-sm">
                    <span className="text-ink">
                      {item.quantity} x {item.product_name}
                    </span>
                    <span className="text-ink-soft">${item.line_total}</span>
                  </div>
                ))}
                <div className="space-y-1.5 border-t border-line pt-3 text-sm">
                  <div className="flex justify-between text-ink-soft">
                    <span>Subtotal</span>
                    <span>${order.subtotal}</span>
                  </div>
                  {Number(order.discount_total) > 0 && (
                    <div className="flex justify-between text-primary">
                      <span>Discount{order.applied_promotion?.code ? ` (${order.applied_promotion.code})` : ""}</span>
                      <span>-${order.discount_total}</span>
                    </div>
                  )}
                  <div className="flex justify-between text-ink-soft">
                    <span>Delivery fee</span>
                    <span>${order.fees}</span>
                  </div>
                  <div className="flex justify-between font-display text-base font-semibold text-ink pt-1.5 border-t border-line">
                    <span>Total</span>
                    <span>${order.total}</span>
                  </div>
                  {totalRefunded > 0 && (
                    <div className="flex justify-between text-primary-dark">
                      <span>Refunded</span>
                      <span>-${totalRefunded.toFixed(2)}</span>
                    </div>
                  )}
                </div>
              </CardBody>
            </Card>

            {payments.length > 0 && (
              <Card>
                <CardHeader className="flex items-center justify-between">
                  <p className="font-medium text-ink flex items-center gap-1.5">
                    <CreditCard className="h-4 w-4" /> Payment
                  </p>
                  {canRequestRefund && (
                    <Button size="sm" variant="secondary" onClick={() => setRefundModalOpen(true)}>
                      <RotateCcw className="h-3.5 w-3.5" /> Request refund
                    </Button>
                  )}
                </CardHeader>
                <CardBody className="space-y-3">
                  {payments.map((payment) => (
                    <div key={payment.id} className="flex items-center justify-between text-sm">
                      <div>
                        <p className="text-ink">${payment.amount} via {payment.method}</p>
                        {payment.failure_reason && <p className="text-xs text-danger mt-0.5">{payment.failure_reason}</p>}
                      </div>
                      <StatusBadge status={payment.status} />
                    </div>
                  ))}
                  {refunds.length > 0 && (
                    <div className="space-y-2 border-t border-line pt-3">
                      {refunds.map((refund) => (
                        <div key={refund.id} className="flex items-center justify-between text-sm">
                          <div>
                            <p className="text-ink">Refund of ${refund.amount}</p>
                            <p className="text-xs text-ink-soft mt-0.5">{refund.reason}</p>
                          </div>
                          <StatusBadge status={refund.status} />
                        </div>
                      ))}
                    </div>
                  )}
                </CardBody>
              </Card>
            )}

            {tracking && (
              <Card>
                <CardHeader className="flex items-center justify-between">
                  <p className="font-medium text-ink flex items-center gap-1.5">
                    <Bike className="h-4 w-4" /> Delivery
                  </p>
                  <StatusBadge status={tracking.delivery.status} />
                </CardHeader>
                <CardBody className="space-y-2 text-sm">
                  <p className="text-ink-soft">
                    Rider: <span className="text-ink">{tracking.delivery.rider_name ?? "Not yet assigned"}</span>
                  </p>
                  {tracking.rider_location ? (
                    <div className="space-y-1">
                      <p className="text-ink-soft">
                        Last known location updated {new Date(tracking.rider_location.recorded_at).toLocaleTimeString()}
                      </p>
                      {tracking.rider_location.is_stale && (
                        <Alert tone="info">The rider's location hasn't updated recently.</Alert>
                      )}
                    </div>
                  ) : (
                    tracking.delivery.status !== "DELIVERED" &&
                    tracking.delivery.status !== "CANCELLED" && (
                      <p className="text-ink-soft">Waiting on the rider's location.</p>
                    )
                  )}
                </CardBody>
              </Card>
            )}

            {reviewable.length > 0 && (
              <Card>
                <CardHeader>
                  <p className="font-medium text-ink flex items-center gap-1.5">
                    <MessageSquare className="h-4 w-4" /> Leave a review
                  </p>
                </CardHeader>
                <CardBody className="space-y-5">
                  {reviewable.map((target) => {
                    const draft = reviewDrafts[target.target_id] ?? { rating: 5, body: "" };
                    const label = TARGET_LABELS[target.target_type] || target.target_name;
                    return (
                      <div key={`${target.target_type}-${target.target_id}`} className="space-y-2 border-b border-line last:border-0 pb-4 last:pb-0">
                        <p className="text-sm text-ink">
                          {target.target_type === "PRODUCT"
                            ? `How was ${target.target_name}?`
                            : `How was ${label} (${target.target_name})?`}
                        </p>
                        {target.existing_review ? (
                          <div className="flex items-center gap-2 text-sm text-ink-soft">
                            <StarPicker value={target.existing_review.rating} onChange={() => {}} />
                            <span>You reviewed this - thank you!</span>
                          </div>
                        ) : (
                          <div className="space-y-2">
                            <StarPicker
                              value={draft.rating}
                              onChange={(rating) => setReviewDrafts((prev) => ({ ...prev, [target.target_id]: { ...draft, rating } }))}
                            />
                            <Textarea
                              label="Comments (optional)"
                              value={draft.body}
                              onChange={(e) =>
                                setReviewDrafts((prev) => ({ ...prev, [target.target_id]: { ...draft, body: e.target.value } }))
                              }
                              placeholder="Tell us more"
                            />
                            <Button
                              size="sm"
                              isLoading={submittingReview === target.target_id}
                              onClick={() => handleSubmitReview(target)}
                            >
                              Submit review
                            </Button>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </CardBody>
              </Card>
            )}

            {order.delivery_address && (
              <Card>
                <CardHeader>
                  <p className="font-medium text-ink flex items-center gap-1.5">
                    <MapPin className="h-4 w-4" /> Delivery address
                  </p>
                </CardHeader>
                <CardBody className="text-sm text-ink-soft space-y-0.5">
                  <p className="text-ink">{order.delivery_address.recipient_name}</p>
                  <p>{order.delivery_address.address_line1}</p>
                  {order.delivery_address.address_line2 && <p>{order.delivery_address.address_line2}</p>}
                  <p>{order.delivery_address.city}{order.delivery_address.state ? `, ${order.delivery_address.state}` : ""}</p>
                  <p>{order.delivery_address.phone}</p>
                </CardBody>
              </Card>
            )}

            <Card>
              <CardHeader>
                <p className="font-medium text-ink">Status history</p>
              </CardHeader>
              <CardBody>
                <ol className="space-y-3">
                  {history.map((entry, index) => (
                    <li key={index} className="flex items-start justify-between gap-3 text-sm">
                      <div>
                        <p className="text-ink">{entry.to_status.replace(/_/g, " ").toLowerCase()}</p>
                        {entry.reason && <p className="text-xs text-ink-soft mt-0.5">{entry.reason}</p>}
                      </div>
                      <span className="shrink-0 text-xs text-ink-soft">
                        {entry.created_at ? new Date(entry.created_at).toLocaleString() : ""}
                      </span>
                    </li>
                  ))}
                </ol>
              </CardBody>
            </Card>

            {order.cancellation_reason && (
              <p className="text-sm text-ink-soft">Cancellation reason: {order.cancellation_reason}</p>
            )}

            {CANCELLABLE_STATUSES.includes(order.status) && (
              <Button variant="danger" onClick={() => setCancelModalOpen(true)}>
                Cancel order
              </Button>
            )}
          </>
        )}
      </div>

      <Modal open={cancelModalOpen} onClose={() => setCancelModalOpen(false)} title="Cancel this order?" description="This can't be undone.">
        <div className="space-y-4">
          <Input
            label="Reason (optional)"
            value={cancelReason}
            onChange={(e) => setCancelReason(e.target.value)}
            placeholder="Changed my mind"
          />
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setCancelModalOpen(false)}>
              Keep order
            </Button>
            <Button variant="danger" isLoading={cancelling} onClick={handleCancel}>
              Cancel order
            </Button>
          </div>
        </div>
      </Modal>

      <Modal
        open={refundModalOpen}
        onClose={() => setRefundModalOpen(false)}
        title="Request a refund"
        description={`Up to $${refundableRemaining.toFixed(2)} is refundable on this order.`}
      >
        <div className="space-y-4">
          <Input
            label="Amount (optional - leave blank for the full refundable amount)"
            value={refundAmount}
            onChange={(e) => setRefundAmount(e.target.value)}
            placeholder={refundableRemaining.toFixed(2)}
          />
          <Textarea
            label="Reason"
            value={refundReason}
            onChange={(e) => setRefundReason(e.target.value)}
            placeholder="What went wrong?"
          />
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setRefundModalOpen(false)}>
              Cancel
            </Button>
            <Button isLoading={requestingRefund} disabled={!refundReason.trim()} onClick={handleRequestRefund}>
              Request refund
            </Button>
          </div>
        </div>
      </Modal>
    </DashboardLayout>
  );
}
