import { useCallback, useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Paperclip } from "lucide-react";
import { DashboardLayout } from "../../../layouts/DashboardLayout";
import { Card, CardBody, CardHeader } from "../../../components/ui/Card";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { Textarea } from "../../../components/ui/Textarea";
import { StatusBadge } from "../../../components/ui/Badge";
import { useAuth } from "../../../context/AuthContext";
import { useToast } from "../../../context/ToastContext";
import { disputeService } from "../../../services/disputeService";
import { extractApiErrorMessage } from "../../../services/apiClient";
import type { Dispute } from "../../../types/disputes";
import { SkeletonBlock } from "../../../components/ui/Skeleton";

export function DisputeDetailPage() {
  const { disputeId } = useParams<{ disputeId: string }>();
  const { user } = useAuth();
  const { showError, showSuccess } = useToast();
  const [dispute, setDispute] = useState<Dispute | null>(null);
  const [loading, setLoading] = useState(true);
  const [reference, setReference] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const base = `/${(user?.role ?? "customer").toLowerCase()}/dashboard`;

  const load = useCallback(() => {
    if (!disputeId) return;
    setLoading(true);
    disputeService
      .getDispute(disputeId)
      .then(setDispute)
      .catch(() => showError("Could not load this dispute."))
      .finally(() => setLoading(false));
  }, [disputeId, showError]);

  useEffect(load, [load]);

  async function submitEvidence() {
    if (!disputeId) return;
    setSubmitting(true);
    try {
      await disputeService.addEvidence(disputeId, "PHOTO", reference || undefined, description || undefined);
      showSuccess("Evidence submitted.");
      setReference("");
      setDescription("");
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not submit evidence."));
    } finally {
      setSubmitting(false);
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

  return (
    <DashboardLayout>
      <div className="space-y-6 max-w-2xl">
        <Link to={`${base}/support`} className="inline-flex items-center gap-1.5 text-sm text-ink-soft hover:text-ink">
          <ArrowLeft className="h-3.5 w-3.5" /> Back to support
        </Link>

        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="font-display text-2xl font-semibold text-ink">{dispute.category.replace(/_/g, " ")}</h1>
            <p className="text-ink-soft mt-1 text-sm">
              {dispute.dispute_number} - Order {dispute.order?.number ?? dispute.order?.id}
            </p>
          </div>
          <StatusBadge status={dispute.status} />
        </div>

        <Card>
          <CardHeader className="font-medium text-ink">Description</CardHeader>
          <CardBody className="text-sm text-ink-soft">{dispute.description}</CardBody>
        </Card>

        {dispute.resolution && (
          <Card>
            <CardHeader className="font-medium text-ink">Resolution</CardHeader>
            <CardBody className="text-sm text-ink-soft">{dispute.resolution}</CardBody>
          </Card>
        )}

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
                  <p className="text-ink">{e.evidence_type}{e.description ? ` - ${e.description}` : ""}</p>
                  {e.secure_reference && <p className="text-xs text-ink-soft mt-0.5">{e.secure_reference}</p>}
                </li>
              ))}
            </ul>
          )}
          <CardBody className="space-y-3 border-t border-line">
            <Input label="Reference (optional)" value={reference} onChange={(e) => setReference(e.target.value)} placeholder="Link to a photo or document" />
            <Textarea label="Description" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Describe this piece of evidence..." rows={2} />
            <div className="flex justify-end">
              <Button size="sm" isLoading={submitting} disabled={!reference.trim() && !description.trim()} onClick={submitEvidence}>
                Submit evidence
              </Button>
            </div>
          </CardBody>
        </Card>

        {(dispute.actions ?? []).length > 0 && (
          <Card>
            <CardHeader className="font-medium text-ink">History</CardHeader>
            <ul className="divide-y divide-line">
              {(dispute.actions ?? []).map((a) => (
                <li key={a.id} className="px-5 py-3 text-sm">
                  <p className="text-ink">{a.action_type.replace(/_/g, " ")}</p>
                  {a.reason && <p className="text-xs text-ink-soft mt-0.5">{a.reason}</p>}
                  <p className="text-xs text-ink-soft mt-0.5">{new Date(a.created_at).toLocaleString()}</p>
                </li>
              ))}
            </ul>
          </Card>
        )}
      </div>
    </DashboardLayout>
  );
}
