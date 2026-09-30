import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Gavel, ChevronLeft, ChevronRight } from "lucide-react";
import { DashboardLayout } from "../../../layouts/DashboardLayout";
import { Card } from "../../../components/ui/Card";
import { Button } from "../../../components/ui/Button";
import { Select } from "../../../components/ui/Select";
import { StatusBadge } from "../../../components/ui/Badge";
import { EmptyState } from "../../../components/ui/EmptyState";
import { useToast } from "../../../context/ToastContext";
import { adminDisputeService } from "../../../services/adminDisputeService";
import type { Dispute } from "../../../types/disputes";
import { SkeletonList } from "../../../components/ui/Skeleton";

const STATUSES = ["OPEN", "INVESTIGATING", "ACTION_REQUIRED", "RESOLVED", "REJECTED", "CLOSED"];
const CATEGORIES = ["MISSING_ITEM", "WRONG_ITEM", "DAMAGED_ITEM", "LATE_DELIVERY", "FAILED_DELIVERY", "PAYMENT_ISSUE", "SERVICE_COMPLAINT", "OTHER"];

export function AdminDisputesPage() {
  const { showError } = useToast();
  const [disputes, setDisputes] = useState<Dispute[]>([]);
  const [status, setStatus] = useState("");
  const [category, setCategory] = useState("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    adminDisputeService
      .listDisputes({ status: status || undefined, category: category || undefined, page })
      .then((r) => {
        setDisputes(r.disputes);
        setTotalPages(r.pagination.total_pages || 1);
      })
      .catch(() => showError("Could not load disputes."))
      .finally(() => setLoading(false));
  }, [status, category, page, showError]);

  useEffect(load, [load]);

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="font-display text-2xl font-semibold text-ink flex items-center gap-2">
              <Gavel className="h-6 w-6" /> Disputes
            </h1>
            <p className="text-ink-soft mt-1">Investigate and resolve disputes over orders, deliveries, and payments.</p>
          </div>
          <div className="flex flex-wrap items-end gap-3">
            <div className="w-48">
              <Select label="Status" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}>
                <option value="">All statuses</option>
                {STATUSES.map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
              </Select>
            </div>
            <div className="w-48">
              <Select label="Category" value={category} onChange={(e) => { setCategory(e.target.value); setPage(1); }}>
                <option value="">All categories</option>
                {CATEGORIES.map((c) => <option key={c} value={c}>{c.replace(/_/g, " ")}</option>)}
              </Select>
            </div>
          </div>
        </div>

        {loading ? (
          <SkeletonList />
        ) : disputes.length === 0 ? (
          <EmptyState icon={<Gavel className="h-5 w-5" />} title="No disputes found" description="No disputes match this filter." />
        ) : (
          <>
            <Card>
              <ul className="divide-y divide-line">
                {disputes.map((dispute) => (
                  <li key={dispute.id}>
                    <Link to={`/admin/dashboard/disputes/${dispute.id}`} className="flex items-center justify-between gap-3 px-5 py-3.5 hover:bg-ink/[0.02]">
                      <div>
                        <p className="font-medium text-ink">{dispute.category.replace(/_/g, " ")}</p>
                        <p className="text-xs text-ink-soft mt-0.5">
                          {dispute.dispute_number} - Order {dispute.order?.number ?? dispute.order?.id} - Opened by {dispute.opened_by?.name} ({dispute.opened_by?.role})
                        </p>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <StatusBadge status={dispute.priority} />
                        <StatusBadge status={dispute.status} />
                      </div>
                    </Link>
                  </li>
                ))}
              </ul>
            </Card>
            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-3">
                <Button variant="secondary" size="sm" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1}>
                  <ChevronLeft className="h-3.5 w-3.5" /> Previous
                </Button>
                <span className="text-sm text-ink-soft">Page {page} of {totalPages}</span>
                <Button variant="secondary" size="sm" onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page >= totalPages}>
                  Next <ChevronRight className="h-3.5 w-3.5" />
                </Button>
              </div>
            )}
          </>
        )}
      </div>
    </DashboardLayout>
  );
}
