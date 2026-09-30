import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, MapPin, Receipt, Bike } from "lucide-react";
import { DashboardLayout } from "../../../layouts/DashboardLayout";
import { Card, CardBody, CardHeader } from "../../../components/ui/Card";
import { Button } from "../../../components/ui/Button";
import { StatusBadge } from "../../../components/ui/Badge";
import { EmptyState } from "../../../components/ui/EmptyState";
import { useToast } from "../../../context/ToastContext";
import { orderService } from "../../../services/orderService";
import { logisticsService } from "../../../services/logisticsService";
import { extractApiErrorMessage } from "../../../services/apiClient";
import { VENDOR_NEXT_STATUS } from "../../../types/order";
import type { Order, OrderStatusHistoryEntry } from "../../../types/order";
import type { DeliveryTracking } from "../../../types/logistics";
import { SkeletonBlock } from "../../../components/ui/Skeleton";

const NEXT_ACTION_LABEL: Record<string, string> = {
  VENDOR_ACCEPTED: "Accept order",
  PREPARING: "Start preparing",
  READY: "Mark ready",
};

export function VendorOrderDetailPage() {
  const { orderId } = useParams<{ orderId: string }>();
  const { showError, showSuccess } = useToast();
  const [order, setOrder] = useState<Order | null>(null);
  const [history, setHistory] = useState<OrderStatusHistoryEntry[]>([]);
  const [tracking, setTracking] = useState<DeliveryTracking | null>(null);
  const [loading, setLoading] = useState(true);
  const [advancing, setAdvancing] = useState(false);

  const load = useCallback(() => {
    if (!orderId) return;
    setLoading(true);
    Promise.all([orderService.getVendorOrder(orderId), orderService.getVendorOrderStatusHistory(orderId)])
      .then(([o, h]) => {
        setOrder(o);
        setHistory(h);
      })
      .catch(() => showError("Could not load this order."))
      .finally(() => setLoading(false));
    // No delivery exists until the order is READY - a 404 just means
    // there's nothing to show here yet.
    logisticsService
      .getVendorOrderDelivery(orderId)
      .then(setTracking)
      .catch(() => setTracking(null));
  }, [orderId, showError]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleAdvance() {
    if (!orderId || !order) return;
    const nextStatus = VENDOR_NEXT_STATUS[order.status];
    if (!nextStatus) return;
    setAdvancing(true);
    try {
      await orderService.transitionVendorOrder(orderId, nextStatus);
      showSuccess("Order updated.");
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not update this order."));
    } finally {
      setAdvancing(false);
    }
  }

  const nextStatus = order ? VENDOR_NEXT_STATUS[order.status] : undefined;

  return (
    <DashboardLayout>
      <div className="space-y-6 max-w-2xl">
        <Link to="/vendor/dashboard/orders" className="inline-flex items-center gap-1.5 text-sm text-ink-soft hover:text-ink">
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
                <p className="text-ink-soft mt-1">{order.branch_name}</p>
              </div>
              <StatusBadge status={order.status} />
            </div>

            {nextStatus && (
              <Button isLoading={advancing} onClick={handleAdvance}>
                {NEXT_ACTION_LABEL[nextStatus] ?? "Advance order"}
              </Button>
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
                <div className="flex justify-between font-display text-base font-semibold text-ink pt-3 border-t border-line">
                  <span>Total</span>
                  <span>${order.total}</span>
                </div>
              </CardBody>
            </Card>

            {tracking && (
              <Card>
                <CardHeader className="flex items-center justify-between">
                  <p className="font-medium text-ink flex items-center gap-1.5">
                    <Bike className="h-4 w-4" /> Delivery
                  </p>
                  <StatusBadge status={tracking.delivery.status} />
                </CardHeader>
                <CardBody className="text-sm text-ink-soft">
                  Rider: <span className="text-ink">{tracking.delivery.rider_name ?? "Not yet assigned"}</span>
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
                  {order.delivery_address.delivery_instructions && (
                    <p className="italic">"{order.delivery_address.delivery_instructions}"</p>
                  )}
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
          </>
        )}
      </div>
    </DashboardLayout>
  );
}
