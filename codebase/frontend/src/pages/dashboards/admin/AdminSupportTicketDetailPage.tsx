import { useCallback, useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Send, Lock, UserPlus } from "lucide-react";
import { DashboardLayout } from "../../../layouts/DashboardLayout";
import { Card, CardBody, CardHeader } from "../../../components/ui/Card";
import { Button } from "../../../components/ui/Button";
import { Select } from "../../../components/ui/Select";
import { Textarea } from "../../../components/ui/Textarea";
import { Toggle } from "../../../components/ui/Toggle";
import { StatusBadge } from "../../../components/ui/Badge";
import { useAuth } from "../../../context/AuthContext";
import { useToast } from "../../../context/ToastContext";
import { adminSupportService } from "../../../services/adminSupportService";
import { extractApiErrorMessage } from "../../../services/apiClient";
import type { SupportTicket } from "../../../types/support";
import { SkeletonBlock } from "../../../components/ui/Skeleton";

const STATUSES = ["OPEN", "IN_PROGRESS", "WAITING_FOR_CUSTOMER", "RESOLVED", "CLOSED"];

export function AdminSupportTicketDetailPage() {
  const { ticketId } = useParams<{ ticketId: string }>();
  const { user } = useAuth();
  const { showError, showSuccess } = useToast();
  const [ticket, setTicket] = useState<SupportTicket | null>(null);
  const [loading, setLoading] = useState(true);
  const [reply, setReply] = useState("");
  const [internal, setInternal] = useState(false);
  const [sending, setSending] = useState(false);
  const [status, setStatus] = useState("");
  const [resolutionSummary, setResolutionSummary] = useState("");
  const [savingStatus, setSavingStatus] = useState(false);

  const load = useCallback(() => {
    if (!ticketId) return;
    setLoading(true);
    adminSupportService
      .getTicket(ticketId)
      .then((t) => {
        setTicket(t);
        setStatus(t.status);
        setResolutionSummary(t.resolution_summary ?? "");
      })
      .catch(() => showError("Could not load this ticket."))
      .finally(() => setLoading(false));
  }, [ticketId, showError]);

  useEffect(load, [load]);

  async function sendReply() {
    if (!ticketId || !reply.trim()) return;
    setSending(true);
    try {
      await adminSupportService.reply(ticketId, reply.trim(), internal ? "INTERNAL" : "PUBLIC");
      setReply("");
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not send this message."));
    } finally {
      setSending(false);
    }
  }

  async function assignToMe() {
    if (!ticketId || !user) return;
    try {
      await adminSupportService.assign(ticketId, user.id);
      showSuccess("Ticket assigned to you.");
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not assign this ticket."));
    }
  }

  async function saveStatus() {
    if (!ticketId) return;
    setSavingStatus(true);
    try {
      await adminSupportService.updateStatus(ticketId, status, resolutionSummary || undefined);
      showSuccess("Ticket status updated.");
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not update ticket status."));
    } finally {
      setSavingStatus(false);
    }
  }

  if (loading) {
    return (
      <DashboardLayout>
        <SkeletonBlock className="h-64" />
      </DashboardLayout>
    );
  }

  if (!ticket) {
    return (
      <DashboardLayout>
        <p className="text-sm text-ink-soft">Ticket not found.</p>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-6 max-w-2xl">
        <Link to="/admin/dashboard/support" className="inline-flex items-center gap-1.5 text-sm text-ink-soft hover:text-ink">
          <ArrowLeft className="h-3.5 w-3.5" /> Back to queue
        </Link>

        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="font-display text-2xl font-semibold text-ink">{ticket.subject}</h1>
            <p className="text-ink-soft mt-1 text-sm">
              {ticket.ticket_number} - {ticket.requester?.name} ({ticket.requester?.role}) - {ticket.category.replace(/_/g, " ")}
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <StatusBadge status={ticket.priority} />
            <StatusBadge status={ticket.status} />
          </div>
        </div>

        <Card>
          <CardHeader className="flex items-center justify-between font-medium text-ink">
            <span>Assignment</span>
            {!ticket.assigned_agent && (
              <Button size="sm" variant="secondary" onClick={assignToMe}>
                <UserPlus className="h-3.5 w-3.5" /> Assign to me
              </Button>
            )}
          </CardHeader>
          <CardBody className="text-sm text-ink-soft">
            {ticket.assigned_agent ? `Assigned to ${ticket.assigned_agent.name}` : "Unassigned"}
          </CardBody>
        </Card>

        <Card>
          <CardHeader className="font-medium text-ink">Conversation</CardHeader>
          <ul className="divide-y divide-line">
            {(ticket.messages ?? []).map((message) => (
              <li key={message.id} className={`px-5 py-3.5 ${message.visibility === "INTERNAL" ? "bg-warning-soft/40" : ""}`}>
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-medium text-ink flex items-center gap-1.5">
                    {message.visibility === "INTERNAL" && <Lock className="h-3 w-3 text-warning" />}
                    {message.sender?.name ?? "System"}
                  </p>
                  <p className="text-xs text-ink-soft">{new Date(message.created_at).toLocaleString()}</p>
                </div>
                <p className="text-sm text-ink-soft mt-1 whitespace-pre-wrap">{message.body}</p>
              </li>
            ))}
          </ul>
        </Card>

        <Card>
          <CardBody className="space-y-3">
            <Textarea label="Reply" value={reply} onChange={(e) => setReply(e.target.value)} placeholder="Type your message..." rows={3} />
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Toggle label="Internal note" checked={internal} onChange={() => setInternal((v) => !v)} />
                <span className="text-sm text-ink-soft">Internal note (not visible to the requester)</span>
              </div>
              <Button size="sm" isLoading={sending} disabled={!reply.trim()} onClick={sendReply}>
                <Send className="h-3.5 w-3.5" /> Send
              </Button>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardHeader className="font-medium text-ink">Update status</CardHeader>
          <CardBody className="space-y-3">
            <Select label="Status" value={status} onChange={(e) => setStatus(e.target.value)}>
              {STATUSES.map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
            </Select>
            {(status === "RESOLVED" || status === "CLOSED") && (
              <Textarea
                label="Resolution summary"
                value={resolutionSummary}
                onChange={(e) => setResolutionSummary(e.target.value)}
                placeholder="Summarize how this was resolved..."
                rows={2}
              />
            )}
            <div className="flex justify-end">
              <Button size="sm" isLoading={savingStatus} onClick={saveStatus}>Save</Button>
            </div>
          </CardBody>
        </Card>
      </div>
    </DashboardLayout>
  );
}
