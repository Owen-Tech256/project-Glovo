import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { LifeBuoy, Gavel, Plus, ChevronLeft, ChevronRight } from "lucide-react";
import { DashboardLayout } from "../../../layouts/DashboardLayout";
import { Card } from "../../../components/ui/Card";
import { Button } from "../../../components/ui/Button";
import { Modal } from "../../../components/ui/Modal";
import { Input } from "../../../components/ui/Input";
import { Select } from "../../../components/ui/Select";
import { Textarea } from "../../../components/ui/Textarea";
import { StatusBadge } from "../../../components/ui/Badge";
import { EmptyState } from "../../../components/ui/EmptyState";
import { useAuth } from "../../../context/AuthContext";
import { useToast } from "../../../context/ToastContext";
import { supportService } from "../../../services/supportService";
import { disputeService } from "../../../services/disputeService";
import { extractApiErrorMessage } from "../../../services/apiClient";
import type { SupportTicket } from "../../../types/support";
import type { Dispute } from "../../../types/disputes";
import { SkeletonList } from "../../../components/ui/Skeleton";

const TICKET_CATEGORIES = ["ORDER_ISSUE", "PAYMENT_ISSUE", "DELIVERY_ISSUE", "ACCOUNT_ISSUE", "VENDOR_ISSUE", "RIDER_ISSUE", "GENERAL", "OTHER"];
const DISPUTE_CATEGORIES = ["MISSING_ITEM", "WRONG_ITEM", "DAMAGED_ITEM", "LATE_DELIVERY", "FAILED_DELIVERY", "PAYMENT_ISSUE", "SERVICE_COMPLAINT", "OTHER"];

function basePathFor(role: string) {
  return `/${role.toLowerCase()}/dashboard`;
}

export function SupportPage() {
  const { user } = useAuth();
  const { showSuccess, showError } = useToast();
  const [tab, setTab] = useState<"tickets" | "disputes">("tickets");
  const base = basePathFor(user?.role ?? "customer");

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink">Support</h1>
          <p className="text-ink-soft mt-1">Get help with an order, or open a dispute over something that went wrong.</p>
        </div>

        <div className="flex flex-wrap gap-1.5 border-b border-line pb-3">
          <button
            onClick={() => setTab("tickets")}
            className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              tab === "tickets" ? "bg-primary-soft text-primary-dark" : "text-ink-soft hover:bg-ink/[0.04] hover:text-ink"
            }`}
          >
            <LifeBuoy className="h-4 w-4" /> Tickets
          </button>
          <button
            onClick={() => setTab("disputes")}
            className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              tab === "disputes" ? "bg-primary-soft text-primary-dark" : "text-ink-soft hover:bg-ink/[0.04] hover:text-ink"
            }`}
          >
            <Gavel className="h-4 w-4" /> Disputes
          </button>
        </div>

        {tab === "tickets" ? (
          <TicketsTab base={base} showSuccess={showSuccess} showError={showError} />
        ) : (
          <DisputesTab base={base} showSuccess={showSuccess} showError={showError} />
        )}
      </div>
    </DashboardLayout>
  );
}

function TicketsTab({
  base,
  showSuccess,
  showError,
}: {
  base: string;
  showSuccess: (m: string) => void;
  showError: (m: string) => void;
}) {
  const [tickets, setTickets] = useState<SupportTicket[]>([]);
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [category, setCategory] = useState("GENERAL");
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [creating, setCreating] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    supportService
      .listMyTickets(status || undefined, page)
      .then((r) => {
        setTickets(r.tickets);
        setTotalPages(r.pagination.total_pages || 1);
      })
      .catch(() => showError("Could not load your tickets."))
      .finally(() => setLoading(false));
  }, [status, page, showError]);

  useEffect(load, [load]);

  async function handleCreate() {
    setCreating(true);
    try {
      await supportService.createTicket({ category, subject, message });
      showSuccess("Ticket created.");
      setModalOpen(false);
      setSubject("");
      setMessage("");
      setCategory("GENERAL");
      setPage(1);
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not create this ticket."));
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div className="w-48">
          <Select label="Status" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}>
            <option value="">All statuses</option>
            <option value="OPEN">Open</option>
            <option value="IN_PROGRESS">In progress</option>
            <option value="WAITING_FOR_CUSTOMER">Waiting for you</option>
            <option value="RESOLVED">Resolved</option>
            <option value="CLOSED">Closed</option>
          </Select>
        </div>
        <Button size="sm" onClick={() => setModalOpen(true)}>
          <Plus className="h-3.5 w-3.5" /> New ticket
        </Button>
      </div>

      {loading ? (
        <SkeletonList />
      ) : tickets.length === 0 ? (
        <EmptyState icon={<LifeBuoy className="h-5 w-5" />} title="No tickets yet" description="Open a ticket if you need help with anything." />
      ) : (
        <>
          <Card>
            <ul className="divide-y divide-line">
              {tickets.map((ticket) => (
                <li key={ticket.id}>
                  <Link to={`${base}/support/${ticket.id}`} className="flex items-center justify-between gap-3 px-5 py-3.5 hover:bg-ink/[0.02]">
                    <div>
                      <p className="font-medium text-ink">{ticket.subject}</p>
                      <p className="text-xs text-ink-soft mt-0.5">
                        {ticket.ticket_number} - {new Date(ticket.created_at).toLocaleString()}
                      </p>
                    </div>
                    <StatusBadge status={ticket.status} />
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

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="New support ticket">
        <div className="space-y-4">
          <Select label="Category" value={category} onChange={(e) => setCategory(e.target.value)}>
            {TICKET_CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {c.replace(/_/g, " ")}
              </option>
            ))}
          </Select>
          <Input label="Subject" value={subject} onChange={(e) => setSubject(e.target.value)} placeholder="Briefly describe the issue" />
          <Textarea label="Message" value={message} onChange={(e) => setMessage(e.target.value)} placeholder="Tell us what happened..." rows={4} />
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setModalOpen(false)}>Cancel</Button>
            <Button isLoading={creating} disabled={!subject.trim() || !message.trim()} onClick={handleCreate}>Submit</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}

function DisputesTab({
  base,
  showSuccess,
  showError,
}: {
  base: string;
  showSuccess: (m: string) => void;
  showError: (m: string) => void;
}) {
  const [disputes, setDisputes] = useState<Dispute[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [orderId, setOrderId] = useState("");
  const [category, setCategory] = useState("MISSING_ITEM");
  const [description, setDescription] = useState("");
  const [creating, setCreating] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    disputeService
      .listMyDisputes(1)
      .then((r) => setDisputes(r.disputes))
      .catch(() => showError("Could not load your disputes."))
      .finally(() => setLoading(false));
  }, [showError]);

  useEffect(load, [load]);

  async function handleCreate() {
    setCreating(true);
    try {
      await disputeService.createDispute({ order_id: orderId.trim(), category, description });
      showSuccess("Dispute opened.");
      setModalOpen(false);
      setOrderId("");
      setDescription("");
      setCategory("MISSING_ITEM");
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not open this dispute."));
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button size="sm" onClick={() => setModalOpen(true)}>
          <Plus className="h-3.5 w-3.5" /> New dispute
        </Button>
      </div>

      {loading ? (
        <SkeletonList />
      ) : disputes.length === 0 ? (
        <EmptyState icon={<Gavel className="h-5 w-5" />} title="No disputes yet" description="Open a dispute if an order had a problem that needs resolving." />
      ) : (
        <Card>
          <ul className="divide-y divide-line">
            {disputes.map((dispute) => (
              <li key={dispute.id}>
                <Link to={`${base}/disputes/${dispute.id}`} className="flex items-center justify-between gap-3 px-5 py-3.5 hover:bg-ink/[0.02]">
                  <div>
                    <p className="font-medium text-ink">{dispute.category.replace(/_/g, " ")}</p>
                    <p className="text-xs text-ink-soft mt-0.5">
                      {dispute.dispute_number} - Order {dispute.order?.number ?? dispute.order?.id} - {new Date(dispute.created_at).toLocaleString()}
                    </p>
                  </div>
                  <StatusBadge status={dispute.status} />
                </Link>
              </li>
            ))}
          </ul>
        </Card>
      )}

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Open a dispute" description="Reference the order this dispute is about by its order ID.">
        <div className="space-y-4">
          <Input label="Order ID" value={orderId} onChange={(e) => setOrderId(e.target.value)} placeholder="Order public ID" />
          <Select label="Category" value={category} onChange={(e) => setCategory(e.target.value)}>
            {DISPUTE_CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {c.replace(/_/g, " ")}
              </option>
            ))}
          </Select>
          <Textarea label="Description" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Describe what went wrong..." rows={4} />
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setModalOpen(false)}>Cancel</Button>
            <Button isLoading={creating} disabled={!orderId.trim() || !description.trim()} onClick={handleCreate}>Submit</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
