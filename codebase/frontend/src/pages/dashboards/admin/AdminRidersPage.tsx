import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bike, ChevronLeft, ChevronRight } from "lucide-react";
import { DashboardLayout } from "../../../layouts/DashboardLayout";
import { Card } from "../../../components/ui/Card";
import { Button } from "../../../components/ui/Button";
import { Select } from "../../../components/ui/Select";
import { StatusBadge } from "../../../components/ui/Badge";
import { EmptyState } from "../../../components/ui/EmptyState";
import { useToast } from "../../../context/ToastContext";
import { logisticsService } from "../../../services/logisticsService";
import type { Rider } from "../../../types/logistics";
import { SkeletonList } from "../../../components/ui/Skeleton";

export function AdminRidersPage() {
  const { showError } = useToast();
  const [riders, setRiders] = useState<Rider[]>([]);
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    logisticsService
      .adminListRiders(status || undefined, page)
      .then((result) => {
        setRiders(result.riders);
        setTotalPages(result.pagination.total_pages || 1);
      })
      .catch(() => showError("Could not load riders."))
      .finally(() => setLoading(false));
  }, [status, page, showError]);

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="font-display text-2xl font-semibold text-ink">Riders</h1>
            <p className="text-ink-soft mt-1">Verify rider onboarding and oversee their status.</p>
          </div>
          <div className="w-48">
            <Select
              label="Onboarding status"
              value={status}
              onChange={(e) => {
                setStatus(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All statuses</option>
              <option value="PENDING">Pending</option>
              <option value="UNDER_REVIEW">Under review</option>
              <option value="APPROVED">Approved</option>
              <option value="REJECTED">Rejected</option>
              <option value="SUSPENDED">Suspended</option>
            </Select>
          </div>
        </div>

        {loading ? (
          <SkeletonList />
        ) : riders.length === 0 ? (
          <EmptyState icon={<Bike className="h-5 w-5" />} title="No riders found" description="No riders match this filter yet." />
        ) : (
          <>
            <Card>
              <ul className="divide-y divide-line">
                {riders.map((rider) => (
                  <li key={rider.id}>
                    <Link
                      to={`/admin/dashboard/riders/${rider.id}`}
                      className="flex items-center justify-between gap-3 px-5 py-3.5 hover:bg-ink/[0.02]"
                    >
                      <div>
                        <p className="font-medium text-ink">{rider.full_name ?? rider.id}</p>
                        <p className="text-xs text-ink-soft mt-0.5">
                          {rider.vehicle ? rider.vehicle.vehicle_type.replace(/_/g, " ").toLowerCase() : "No vehicle on file"}
                        </p>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <StatusBadge status={rider.operational_status} />
                        <StatusBadge status={rider.onboarding_status} />
                      </div>
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
