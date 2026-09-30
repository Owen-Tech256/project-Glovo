import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { LifeBuoy, ChevronLeft, ChevronRight } from "lucide-react";
import { DashboardLayout } from "../../../layouts/DashboardLayout";
import { Card } from "../../../components/ui/Card";
import { Button } from "../../../components/ui/Button";
import { Select } from "../../../components/ui/Select";
import { Toggle } from "../../../components/ui/Toggle";
import { StatusBadge } from "../../../components/ui/Badge";
import { EmptyState } from "../../../components/ui/EmptyState";
import { useToast } from "../../../context/ToastContext";
import { adminSupportService } from "../../../services/adminSupportService";
import type { SupportTicket } from "../../../types/support";
import { SkeletonList } from "../../../components/ui/Skeleton";

const STATUSES = ["OPEN", "IN_PROGRESS", "WAITING_FOR_CUSTOMER", "RESOLVED", "CLOSED"];
const CATEGORIES = ["ORDER_ISSUE", "PAYMENT_ISSUE", "DELIVERY_ISSUE", "ACCOUNT_ISSUE", "VENDOR_ISSUE", "RIDER_ISSUE", "GENERAL", "OTHER"];

export function AdminSupportPage() {
  const { showError } = useToast();
  const [tickets, setTickets] = useState<SupportTicket[]>([]);
  const [status, setStatus] = useState("");
  const [category, setCategory] = useState("");
  const [unassignedOnly, setUnassignedOnly] = useState(false);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    adminSupportService
      .listTickets({ status: status || undefined, category: category || undefined, unassigned: unassignedOnly, page })
      .then((r) => {
        setTickets(r.tickets);
        setTotalPages(r.pagination.total_pages || 1);
      })
      .catch(() => showError("Could not load the ticket queue."))
      .finally(() => setLoading(false));
  }, [status, category, unassignedOnly, page, showError]);

  useEffect(load, [load]);

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="font-display text-2xl font-semibold text-ink flex items-center gap-2">
              <LifeBuoy className="h-6 w-6" /> Support
            </h1>
            <p className="text-ink-soft mt-1">Triage and respond to customer, vendor, and rider tickets.</p>
          </div>
          <div className="flex flex-wrap items-end gap-3">
            <div className="w-44">
              <Select label="Status" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}>
                <option value="">All statuses</option>
                {STATUSES.map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
              </Select>
            </div>
            <div className="w-44">
              <Select label="Category" value={category} onChange={(e) => { setCategory(e.target.value); setPage(1); }}>
                <option value="">All categories</option>
                {CATEGORIES.map((c) => <option key={c} value={c}>{c.replace(/_/g, " ")}</option>)}
              </Select>
            </div>
            <div className="flex items-center gap-2 pb-2.5">
              <Toggle
                label="Unassigned only"
                checked={unassignedOnly}
                onChange={() => { setUnassignedOnly((v) => !v); setPage(1); }}
              />
              <span className="text-sm text-ink-soft">Unassigned only</span>
            </div>
          </div>
        </div>

        {loading ? (
          <SkeletonList />
        ) : tickets.length === 0 ? (
          <EmptyState icon={<LifeBuoy className="h-5 w-5" />} title="No tickets found" description="No tickets match this filter." />
        ) : (
          <>
            <Card>
              <ul className="divide-y divide-line">
                {tickets.map((ticket) => (
                  <li key={ticket.id}>
                    <Link to={`/admin/dashboard/support/${ticket.id}`} className="flex items-center justify-between gap-3 px-5 py-3.5 hover:bg-ink/[0.02]">
                      <div>
                        <p className="font-medium text-ink">{ticket.subject}</p>
                        <p className="text-xs text-ink-soft mt-0.5">
                          {ticket.ticket_number} - {ticket.requester?.name} ({ticket.requester?.role}) - {ticket.assigned_agent ? `Assigned to ${ticket.assigned_agent.name}` : "Unassigned"}
                        </p>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <StatusBadge status={ticket.priority} />
                        <StatusBadge status={ticket.status} />
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
