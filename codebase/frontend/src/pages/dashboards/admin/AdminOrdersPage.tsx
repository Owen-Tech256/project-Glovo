import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ChevronLeft, ChevronRight, ClipboardList } from "lucide-react";
import { DashboardLayout } from "../../../layouts/DashboardLayout";
import { Card } from "../../../components/ui/Card";
import { Button } from "../../../components/ui/Button";
import { Select } from "../../../components/ui/Select";
import { StatusBadge } from "../../../components/ui/Badge";
import { EmptyState } from "../../../components/ui/EmptyState";
import { useToast } from "../../../context/ToastContext";
import { orderService } from "../../../services/orderService";
import type { Order } from "../../../types/order";
import { SkeletonList } from "../../../components/ui/Skeleton";

export function AdminOrdersPage() {
  const { showError } = useToast();
  const [orders, setOrders] = useState<Order[]>([]);
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    orderService
      .listAllOrders({ status: status || undefined, page })
      .then((result) => {
        setOrders(result.orders);
        setTotalPages(result.pagination.total_pages || 1);
      })
      .catch(() => showError("Could not load orders."))
      .finally(() => setLoading(false));
  }, [status, page, showError]);

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="font-display text-2xl font-semibold text-ink">Order oversight</h1>
            <p className="text-ink-soft mt-1">Read-only visibility into orders across the platform.</p>
          </div>
          <div className="w-48">
            <Select
              label="Status"
              value={status}
              onChange={(e) => {
                setStatus(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All statuses</option>
              <option value="CREATED">Created</option>
              <option value="PENDING_PAYMENT">Pending payment</option>
              <option value="PAYMENT_CONFIRMED">Payment confirmed</option>
              <option value="VENDOR_ACCEPTED">Vendor accepted</option>
              <option value="PREPARING">Preparing</option>
              <option value="READY">Ready</option>
              <option value="CANCELLED">Cancelled</option>
            </Select>
          </div>
        </div>

        {loading ? (
          <SkeletonList />
        ) : orders.length === 0 ? (
          <EmptyState icon={<ClipboardList className="h-5 w-5" />} title="No orders found" description="No orders match this filter yet." />
        ) : (
          <>
            <Card>
              <ul className="divide-y divide-line">
                {orders.map((order) => (
                  <li key={order.id}>
                    <Link
                      to={`/admin/dashboard/orders/${order.id}`}
                      className="flex items-center justify-between gap-3 px-5 py-3.5 hover:bg-ink/[0.02]"
                    >
                      <div>
                        <p className="font-medium text-ink">{order.order_number}</p>
                        <p className="text-xs text-ink-soft mt-0.5">
                          {order.vendor_name ? `${order.vendor_name} - ` : ""}
                          {order.branch_name} - ${order.total}
                        </p>
                      </div>
                      <StatusBadge status={order.status} />
                    </Link>
                  </li>
                ))}
              </ul>
            </Card>

            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-3">
                <Button variant="secondary" size="sm" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1}>
                  <ChevronLeft className="h-3.5 w-3.5" />
                  Previous
                </Button>
                <span className="text-sm text-ink-soft">
                  Page {page} of {totalPages}
                </span>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                >
                  Next
                  <ChevronRight className="h-3.5 w-3.5" />
                </Button>
              </div>
            )}
          </>
        )}
      </div>
    </DashboardLayout>
  );
}
