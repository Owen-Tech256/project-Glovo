import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Truck, ChevronLeft, ChevronRight, Radar, TriangleAlert } from "lucide-react";
import { DashboardLayout } from "../../../layouts/DashboardLayout";
import { Card, CardBody } from "../../../components/ui/Card";
import { Button } from "../../../components/ui/Button";
import { Select } from "../../../components/ui/Select";
import { StatusBadge } from "../../../components/ui/Badge";
import { EmptyState } from "../../../components/ui/EmptyState";
import { useToast } from "../../../context/ToastContext";
import { logisticsService } from "../../../services/logisticsService";
import type { Delivery, DispatchHealth } from "../../../types/logistics";
import { SkeletonBlock, SkeletonList } from "../../../components/ui/Skeleton";

function DispatchHealthCard({ health, onFilterStatus }: { health: DispatchHealth; onFilterStatus: (status: string) => void }) {
  return (
    <Card>
      <CardBody className="space-y-3">
        <div className="flex items-center gap-2 text-ink-soft">
          <Radar className="h-4 w-4" />
          <p className="text-sm font-medium text-ink">Dispatch health</p>
        </div>
        <div className="grid grid-cols-3 gap-3">
          <button onClick={() => onFilterStatus("SEARCHING")} className="rounded-md border border-line px-3 py-2 text-left hover:bg-ink/[0.02]">
            <p className="text-xl font-display font-semibold text-ink">{health.searching_count}</p>
            <p className="text-xs text-ink-soft">Searching for a rider</p>
          </button>
          <button onClick={() => onFilterStatus("OFFERED")} className="rounded-md border border-line px-3 py-2 text-left hover:bg-ink/[0.02]">
            <p className="text-xl font-display font-semibold text-ink">{health.offered_count}</p>
            <p className="text-xs text-ink-soft">Offered, awaiting response</p>
          </button>
          <div className={`rounded-md border px-3 py-2 ${health.stuck_count > 0 ? "border-warning/30 bg-warning-soft" : "border-line"}`}>
            <p className={`text-xl font-display font-semibold ${health.stuck_count > 0 ? "text-warning" : "text-ink"}`}>
              {health.stuck_count}
            </p>
            <p className="text-xs text-ink-soft">
              Stuck over {Math.round(health.stuck_threshold_seconds / 60)} min
            </p>
          </div>
        </div>
        {health.stuck_count > 0 && (
          <div className="flex items-start gap-2 rounded-md bg-warning-soft border border-warning/20 px-3 py-2.5 text-sm text-warning">
            <TriangleAlert className="h-4 w-4 shrink-0" />
            <div>
              {health.stuck_deliveries.length} deliver{health.stuck_deliveries.length === 1 ? "y hasn't" : "ies haven't"} found a
              rider in time - review and reassign as needed:{" "}
              {health.stuck_deliveries.slice(0, 5).map((d, i) => (
                <span key={d.id}>
                  {i > 0 && ", "}
                  <Link to={`/admin/dashboard/deliveries/${d.id}`} className="underline underline-offset-2">
                    {d.order_number ?? d.id}
                  </Link>
                </span>
              ))}
            </div>
          </div>
        )}
      </CardBody>
    </Card>
  );
}

export function AdminDeliveriesPage() {
  const { showError } = useToast();
  const [deliveries, setDeliveries] = useState<Delivery[]>([]);
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [health, setHealth] = useState<DispatchHealth | null>(null);
  const [healthLoading, setHealthLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    logisticsService
      .adminListDeliveries({ status: status || undefined, page })
      .then((result) => {
        setDeliveries(result.deliveries);
        setTotalPages(result.pagination.total_pages || 1);
      })
      .catch(() => showError("Could not load deliveries."))
      .finally(() => setLoading(false));
  }, [status, page, showError]);

  useEffect(() => {
    logisticsService
      .adminGetDispatchHealth()
      .then(setHealth)
      .catch(() => showError("Could not load dispatch health."))
      .finally(() => setHealthLoading(false));
  }, [showError]);

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="font-display text-2xl font-semibold text-ink">Deliveries</h1>
            <p className="text-ink-soft mt-1">Monitor dispatch and intervene when needed.</p>
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
              <option value="SEARCHING">Searching</option>
              <option value="OFFERED">Offered</option>
              <option value="ASSIGNED">Assigned</option>
              <option value="PICKED_UP">Picked up</option>
              <option value="DELIVERING">Delivering</option>
              <option value="DELIVERED">Delivered</option>
              <option value="CANCELLED">Cancelled</option>
            </Select>
          </div>
        </div>

        {healthLoading ? (
          <SkeletonBlock className="h-32" />
        ) : (
          health && (
            <DispatchHealthCard
              health={health}
              onFilterStatus={(s) => {
                setStatus(s);
                setPage(1);
              }}
            />
          )
        )}

        {loading ? (
          <SkeletonList />
        ) : deliveries.length === 0 ? (
          <EmptyState icon={<Truck className="h-5 w-5" />} title="No deliveries found" description="No deliveries match this filter yet." />
        ) : (
          <>
            <Card>
              <ul className="divide-y divide-line">
                {deliveries.map((delivery) => (
                  <li key={delivery.id}>
                    <Link
                      to={`/admin/dashboard/deliveries/${delivery.id}`}
                      className="flex items-center justify-between gap-3 px-5 py-3.5 hover:bg-ink/[0.02]"
                    >
                      <div>
                        <p className="font-medium text-ink">{delivery.order_number ?? delivery.order_id}</p>
                        <p className="text-xs text-ink-soft mt-0.5">
                          {delivery.branch_name ?? "Branch"}
                          {delivery.rider_name ? ` - ${delivery.rider_name}` : " - unassigned"}
                        </p>
                      </div>
                      <StatusBadge status={delivery.status} />
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
