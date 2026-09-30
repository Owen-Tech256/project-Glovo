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
import { vendorService } from "../../../services/vendorService";
import type { Order } from "../../../types/order";
import type { Branch } from "../../../types/catalog";
import { SkeletonList } from "../../../components/ui/Skeleton";

export function VendorOrderQueuePage() {
  const { showError } = useToast();
  const [orders, setOrders] = useState<Order[]>([]);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [status, setStatus] = useState("");
  const [branchId, setBranchId] = useState("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    vendorService.listMyBranches().then(setBranches).catch(() => undefined);
  }, []);

  useEffect(() => {
    setLoading(true);
    orderService
      .listVendorOrders({ status: status || undefined, branchId: branchId || undefined, page })
      .then((result) => {
        setOrders(result.orders);
        setTotalPages(result.pagination.total_pages || 1);
      })
      .catch(() => showError("Could not load your order queue."))
      .finally(() => setLoading(false));
  }, [status, branchId, page, showError]);

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="font-display text-2xl font-semibold text-ink">Orders</h1>
            <p className="text-ink-soft mt-1">Incoming orders across your branches.</p>
          </div>
          <div className="flex gap-3">
            {branches.length > 1 && (
              <div className="w-44">
                <Select
                  label="Branch"
                  value={branchId}
                  onChange={(e) => {
                    setBranchId(e.target.value);
                    setPage(1);
                  }}
                >
                  <option value="">All branches</option>
                  {branches.map((branch) => (
                    <option key={branch.id} value={branch.id}>
                      {branch.name}
                    </option>
                  ))}
                </Select>
              </div>
            )}
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
                <option value="PAYMENT_CONFIRMED">New (payment confirmed)</option>
                <option value="VENDOR_ACCEPTED">Accepted</option>
                <option value="PREPARING">Preparing</option>
                <option value="READY">Ready</option>
                <option value="CANCELLED">Cancelled</option>
              </Select>
            </div>
          </div>
        </div>

        {loading ? (
          <SkeletonList />
        ) : orders.length === 0 ? (
          <EmptyState icon={<ClipboardList className="h-5 w-5" />} title="No orders" description="No orders match this filter yet." />
        ) : (
          <>
            <Card>
              <ul className="divide-y divide-line">
                {orders.map((order) => (
                  <li key={order.id}>
                    <Link
                      to={`/vendor/dashboard/orders/${order.id}`}
                      className="flex items-center justify-between gap-3 px-5 py-3.5 hover:bg-ink/[0.02]"
                    >
                      <div>
                        <p className="font-medium text-ink">{order.order_number}</p>
                        <p className="text-xs text-ink-soft mt-0.5">{order.branch_name} - ${order.total}</p>
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
