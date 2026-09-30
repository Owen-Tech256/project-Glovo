import { useCallback, useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Paperclip, History } from "lucide-react";
import { DashboardLayout } from "../../../layouts/DashboardLayout";
import { Card, CardBody, CardHeader } from "../../../components/ui/Card";
import { Button } from "../../../components/ui/Button";
import { Select } from "../../../components/ui/Select";
import { Input } from "../../../components/ui/Input";
import { Textarea } from "../../../components/ui/Textarea";
import { StatusBadge } from "../../../components/ui/Badge";
import { useToast } from "../../../context/ToastContext";
import { adminDisputeService } from "../../../services/adminDisputeService";
import { extractApiErrorMessage } from "../../../services/apiClient";
import type { Dispute } from "../../../types/disputes";
import { SkeletonBlock } from "../../../components/ui/Skeleton";

const PRIORITIES = ["LOW", "NORMAL", "HIGH", "URGENT"];
const ACTION_TYPES = ["NOTE", "REQUEST_INFO", "REPLACEMENT_APPROVED", "ESCALATED", "REJECTED", "OTHER"];
const RESOLVE_STATUSES = ["RESOLVED", "REJECTED", "CLOSED"];

export function AdminDisputeDetailPage() {
  const { disputeId } = useParams<{ disputeId: string }>();
  const { showError, showSuccess } = useToast();
  const [dispute, setDispute] = useState<Dispute | null>(null);
  const [loading, setLoading] = useState(true);

  const [actionType, setActionType] = useState("NOTE");
  const [actionReason, setActionReason] = useState("");
  const [recordingAction, setRecordingAction] = useState(false);

  const [resolveStatus, setResolveStatus] = useState("RESOLVED");
  const [resolution, setResolution] = useState("");
  const [resolving, setResolving] = useState(false);

  const [refundAmount, setRefundAmount] = useState("");
  const [refundReason, setRefundReason] = useState("");
  const [refunding, setRefunding] = useState(false);

  const load = useCallback(() => {
    if (!disputeId) return;
    setLoading(true);
    adminDisputeService
      .getDispute(disputeId)
      .then(setDispute)
      .catch(() => showError("Could not load this dispute."))
      .finally(() => setLoading(false));
  }, [disputeId, showError]);

  useEffect(load, [load]);

  async function updatePriority(priority: string) {
    if (!disputeId) return;
    try {
      await adminDisputeService.updatePriority(disputeId, priority);
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not update priority."));
    }
  }

  async function recordAction() {
    if (!disputeId) return;
    setRecordingAction(true);
    try {
      await adminDisputeService.recordAction(disputeId, actionType, actionReason || undefined);
      showSuccess("Action recorded.");
      setActionReason("");
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not record this action."));
    } finally {
      setRecordingAction(false);
    }
  }

  async function resolve() {
    if (!disputeId) return;
    setResolving(true);
    try {
      await adminDisputeService.resolve(disputeId, resolveStatus, resolution || undefined);
      showSuccess("Dispute updated.");
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not resolve this dispute."));
    } finally {
      setResolving(false);
    }
  }

  async function resolveWithRefund() {
    if (!disputeId || !refundReason.trim()) return;
    setRefunding(true);
    try {
      await adminDisputeService.resolveWithRefund(disputeId, refundReason.trim(), refundAmount.trim() || undefined);
      showSuccess("Dispute resolved with a refund.");
      setRefundAmount("");
      setRefundReason("");
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not process this refund."));
    } finally {
      setRefunding(false);
    }
  }

  if (loading) {
    return (
      <DashboardLayout>
        <SkeletonBlock className="h-64" />
      </DashboardLayout>
    );
  }

  if (!dispute) {
    return (
      <DashboardLayout>
        <p className="text-sm text-ink-soft">Dispute not found.</p>
      </DashboardLayout>
    );
  }

  const isResolved = ["RESOLVED", "REJECTED", "CLOSED"].includes(dispute.status);

  return (
    <DashboardLayout>
      <div className="space-y-6 max-w-2xl">
        <Link to="/admin/dashboard/disputes" className="inline-flex items-center gap-1.5 text-sm text-ink-soft hover:text-ink">
          <ArrowLeft className="h-3.5 w-3.5" /> Back to disputes
        </Link>

        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="font-display text-2xl font-semibold text-ink">{dispute.category.replace(/_/g, " ")}</h1>
            <p className="text-ink-soft mt-1 text-sm">
              {dispute.dispute_number} - Order {dispute.order?.number ?? dispute.order?.id} - Opened by {dispute.opened_by?.name} ({dispute.opened_by?.role})
            </p>
          </div>
          <StatusBadge status={dispute.status} />
        </div>

        <Card>
          <CardHeader className="font-medium text-ink">Description</CardHeader>
          <CardBody className="text-sm text-ink-soft">{dispute.description}</CardBody>
        </Card>

        <Card>
          <CardHeader className="font-medium text-ink">Priority</CardHeader>
          <CardBody>
            <div className="w-44">
              <Select label="Priority" value={dispute.priority} onChange={(e) => updatePriority(e.target.value)}>
                {PRIORITIES.map((p) => <option key={p} value={p}>{p}</option>)}
              </Select>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardHeader className="flex items-center gap-2 font-medium text-ink">
            <Paperclip className="h-4 w-4 text-primary" /> Evidence
          </CardHeader>
          {(dispute.evidence ?? []).length === 0 ? (
            <CardBody className="text-sm text-ink-soft">No evidence submitted yet.</CardBody>
          ) : (
            <ul className="divide-y divide-line">
              {(dispute.evidence ?? []).map((e) => (
                <li key={e.id} className="px-5 py-3 text-sm">
                  <p className="text-ink">{e.evidence_type}{e.description ? ` - ${e.description}` : ""} <span className="text-xs text-ink-soft">by {e.submitted_by?.name}</span></p>
                  {e.secure_reference && <p className="text-xs text-ink-soft mt-0.5">{e.secure_reference}</p>}
                </li>
              ))}
            </ul>
          )}
        </Card>

        {(dispute.actions ?? []).length > 0 && (
          <Card>
            <CardHeader className="flex items-center gap-2 font-medium text-ink">
              <History className="h-4 w-4 text-primary" /> Action history
            </CardHeader>
            <ul className="divide-y divide-line">
              {(dispute.actions ?? []).map((a) => (
                <li key={a.id} className="px-5 py-3 text-sm">
                  <p className="text-ink">{a.action_type.replace(/_/g, " ")} <span className="text-xs text-ink-soft">by {a.actor?.name}</span></p>
                  {a.reason && <p className="text-xs text-ink-soft mt-0.5">{a.reason}</p>}
                  <p className="text-xs text-ink-soft mt-0.5">{new Date(a.created_at).toLocaleString()}</p>
                </li>
              ))}
            </ul>
          </Card>
        )}

        {!isResolved && (
          <>
            <Card>
              <CardHeader className="font-medium text-ink">Record an action</CardHeader>
              <CardBody className="space-y-3">
                <Select label="Action" value={actionType} onChange={(e) => setActionType(e.target.value)}>
                  {ACTION_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
                </Select>
                <Textarea label="Reason / note" value={actionReason} onChange={(e) => setActionReason(e.target.value)} rows={2} />
                <div className="flex justify-end">
                  <Button size="sm" variant="secondary" isLoading={recordingAction} onClick={recordAction}>Record</Button>
                </div>
              </CardBody>
            </Card>

            <Card>
              <CardHeader className="font-medium text-ink">Resolve without a refund</CardHeader>
              <CardBody className="space-y-3">
                <Select label="Outcome" value={resolveStatus} onChange={(e) => setResolveStatus(e.target.value)}>
                  {RESOLVE_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                </Select>
                <Textarea label="Resolution notes" value={resolution} onChange={(e) => setResolution(e.target.value)} rows={2} />
                <div className="flex justify-end">
                  <Button size="sm" isLoading={resolving} onClick={resolve}>Save outcome</Button>
                </div>
              </CardBody>
            </Card>

            <Card>
              <CardHeader className="font-medium text-ink">Resolve with a refund</CardHeader>
              <CardBody className="space-y-3">
                <p className="text-xs text-ink-soft">Requires the finance admin permission. Leave amount blank for a full refund.</p>
                <Input label="Amount (optional)" value={refundAmount} onChange={(e) => setRefundAmount(e.target.value)} placeholder="e.g. 5.00" />
                <Textarea label="Reason" value={refundReason} onChange={(e) => setRefundReason(e.target.value)} rows={2} />
                <div className="flex justify-end">
                  <Button size="sm" variant="danger" isLoading={refunding} disabled={!refundReason.trim()} onClick={resolveWithRefund}>
                    Issue refund & resolve
                  </Button>
                </div>
              </CardBody>
            </Card>
          </>
        )}
      </div>
    </DashboardLayout>
  );
}
