import { useCallback, useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Send } from "lucide-react";
import { DashboardLayout } from "../../../layouts/DashboardLayout";
import { Card, CardBody, CardHeader } from "../../../components/ui/Card";
import { Button } from "../../../components/ui/Button";
import { Textarea } from "../../../components/ui/Textarea";
import { StatusBadge } from "../../../components/ui/Badge";
import { useAuth } from "../../../context/AuthContext";
import { useToast } from "../../../context/ToastContext";
import { supportService } from "../../../services/supportService";
import { extractApiErrorMessage } from "../../../services/apiClient";
import type { SupportTicket } from "../../../types/support";
import { SkeletonBlock } from "../../../components/ui/Skeleton";

export function SupportTicketDetailPage() {
  const { ticketId } = useParams<{ ticketId: string }>();
  const { user } = useAuth();
  const { showError } = useToast();
  const [ticket, setTicket] = useState<SupportTicket | null>(null);
  const [loading, setLoading] = useState(true);
  const [reply, setReply] = useState("");
  const [sending, setSending] = useState(false);
  const base = `/${(user?.role ?? "customer").toLowerCase()}/dashboard`;

  const load = useCallback(() => {
    if (!ticketId) return;
    setLoading(true);
    supportService
      .getTicket(ticketId)
      .then(setTicket)
      .catch(() => showError("Could not load this ticket."))
      .finally(() => setLoading(false));
  }, [ticketId, showError]);

  useEffect(load, [load]);

  async function sendReply() {
    if (!ticketId || !reply.trim()) return;
    setSending(true);
    try {
      await supportService.reply(ticketId, reply.trim());
      setReply("");
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not send this message."));
    } finally {
      setSending(false);
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

  const closed = ticket.status === "CLOSED";

  return (
    <DashboardLayout>
      <div className="space-y-6 max-w-2xl">
        <Link to={`${base}/support`} className="inline-flex items-center gap-1.5 text-sm text-ink-soft hover:text-ink">
          <ArrowLeft className="h-3.5 w-3.5" /> Back to support
        </Link>

        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="font-display text-2xl font-semibold text-ink">{ticket.subject}</h1>
            <p className="text-ink-soft mt-1 text-sm">
              {ticket.ticket_number} - {ticket.category.replace(/_/g, " ")}
            </p>
          </div>
          <StatusBadge status={ticket.status} />
        </div>

        {ticket.resolution_summary && (
          <Card>
            <CardHeader className="font-medium text-ink">Resolution</CardHeader>
            <CardBody className="text-sm text-ink-soft">{ticket.resolution_summary}</CardBody>
          </Card>
        )}

        <Card>
          <CardHeader className="font-medium text-ink">Conversation</CardHeader>
          <ul className="divide-y divide-line">
            {(ticket.messages ?? []).map((message) => {
              const isMe = message.sender?.id === user?.id;
              return (
                <li key={message.id} className="px-5 py-3.5">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm font-medium text-ink">{isMe ? "You" : message.sender?.name ?? "Support"}</p>
                    <p className="text-xs text-ink-soft">{new Date(message.created_at).toLocaleString()}</p>
                  </div>
                  <p className="text-sm text-ink-soft mt-1 whitespace-pre-wrap">{message.body}</p>
                </li>
              );
            })}
          </ul>
        </Card>

        {!closed ? (
          <Card>
            <CardBody className="space-y-3">
              <Textarea label="Reply" value={reply} onChange={(e) => setReply(e.target.value)} placeholder="Type your message..." rows={3} />
              <div className="flex justify-end">
                <Button size="sm" isLoading={sending} disabled={!reply.trim()} onClick={sendReply}>
                  <Send className="h-3.5 w-3.5" /> Send
                </Button>
              </div>
            </CardBody>
          </Card>
        ) : (
          <p className="text-sm text-ink-soft">This ticket is closed.</p>
        )}
      </div>
    </DashboardLayout>
  );
}
