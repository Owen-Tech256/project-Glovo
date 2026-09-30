import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, MapPin, Receipt } from "lucide-react";
import { DashboardLayout } from "../../../layouts/DashboardLayout";
import { Card, CardBody, CardHeader } from "../../../components/ui/Card";
import { StatusBadge } from "../../../components/ui/Badge";
import { EmptyState } from "../../../components/ui/EmptyState";
import { useToast } from "../../../context/ToastContext";
import { orderService } from "../../../services/orderService";
import type { Order, OrderStatusHistoryEntry } from "../../../types/order";
import { SkeletonBlock } from "../../../components/ui/Skeleton";

export function AdminOrderDetailPage() {
  const { orderId } = useParams<{ orderId: string }>();
  const { showError } = useToast();
  const [order, setOrder] = useState<Order | null>(null);
  const [history, setHistory] = useState<OrderStatusHistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!orderId) return;
    setLoading(true);
    Promise.all([orderService.getAnyOrder(orderId), orderService.getAnyOrderStatusHistory(orderId)])
      .then(([o, h]) => {
        setOrder(o);
        setHistory(h);
      })
      .catch(() => showError("Could not load this order."))
      .finally(() => setLoading(false));
  }, [orderId, showError]);

  return (
    <DashboardLayout>
      <div className="space-y-6 max-w-2xl">
        <Link to="/admin/dashboard/orders" className="inline-flex items-center gap-1.5 text-sm text-ink-soft hover:text-ink">
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
                  <div className="flex justify-between text-ink-soft">
                    <span>Delivery fee</span>
                    <span>${order.fees}</span>
                  </div>
                  <div className="flex justify-between font-display text-base font-semibold text-ink pt-1.5 border-t border-line">
                    <span>Total</span>
                    <span>${order.total}</span>
                  </div>
                </div>
              </CardBody>
            </Card>

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
                  <p>{order.delivery_address.city}{order.delivery_address.state ? `, ${order.delivery_address.state}` : ""}</p>
                  <p>{order.delivery_address.phone}</p>
                </CardBody>
              </Card>
            )}

            {order.cancellation_reason && (
              <p className="text-sm text-ink-soft">Cancellation reason: {order.cancellation_reason}</p>
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
                        {entry.changed_by_role && <p className="text-xs text-ink-soft">by {entry.changed_by_role.toLowerCase()}</p>}
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
