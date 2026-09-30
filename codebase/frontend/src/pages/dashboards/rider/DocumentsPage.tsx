import { type FormEvent, useEffect, useState } from "react";
import { FileCheck, Plus } from "lucide-react";
import { DashboardLayout } from "../../../layouts/DashboardLayout";
import { Card } from "../../../components/ui/Card";
import { Button } from "../../../components/ui/Button";
import { Select } from "../../../components/ui/Select";
import { Input } from "../../../components/ui/Input";
import { Modal } from "../../../components/ui/Modal";
import { StatusBadge } from "../../../components/ui/Badge";
import { EmptyState } from "../../../components/ui/EmptyState";
import { useToast } from "../../../context/ToastContext";
import { logisticsService } from "../../../services/logisticsService";
import { extractApiErrorMessage } from "../../../services/apiClient";
import type { RiderDocument } from "../../../types/logistics";
import { SkeletonBlock } from "../../../components/ui/Skeleton";

const DOCUMENT_TYPES = ["GOVERNMENT_ID", "DRIVERS_LICENSE", "VEHICLE_REGISTRATION", "INSURANCE", "BACKGROUND_CHECK", "OTHER"];

export function DocumentsPage() {
  const { showSuccess, showError } = useToast();
  const [documents, setDocuments] = useState<RiderDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [documentType, setDocumentType] = useState("GOVERNMENT_ID");
  const [reference, setReference] = useState("");
  const [expiryDate, setExpiryDate] = useState("");

  const load = () => {
    setLoading(true);
    logisticsService
      .listDocuments()
      .then(setDocuments)
      .catch(() => showError("Could not load your documents."))
      .finally(() => setLoading(false));
  };

  useEffect(load, [showError]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    try {
      await logisticsService.submitDocument({
        document_type: documentType,
        reference,
        expiry_date: expiryDate || null,
      });
      showSuccess("Document submitted for review.");
      setModalOpen(false);
      setReference("");
      setExpiryDate("");
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not submit this document."));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6 max-w-2xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="font-display text-2xl font-semibold text-ink">Documents</h1>
            <p className="text-ink-soft mt-1">Submit verification documents for review.</p>
          </div>
          <Button onClick={() => setModalOpen(true)}>
            <Plus className="h-4 w-4" />
            Submit document
          </Button>
        </div>

        {loading ? (
          <SkeletonBlock className="h-64" />
        ) : documents.length === 0 ? (
          <EmptyState icon={<FileCheck className="h-5 w-5" />} title="No documents yet" description="Submit a document to begin verification." />
        ) : (
          <Card>
            <ul className="divide-y divide-line">
              {documents.map((doc) => (
                <li key={doc.id} className="flex items-center justify-between gap-3 px-5 py-3.5">
                  <div>
                    <p className="font-medium text-ink text-sm">{doc.document_type.replace(/_/g, " ")}</p>
                    <p className="text-xs text-ink-soft mt-0.5">
                      {doc.reference}
                      {doc.expiry_date ? ` - expires ${doc.expiry_date}` : ""}
                    </p>
                    {doc.review_notes && <p className="text-xs text-ink-soft mt-0.5 italic">"{doc.review_notes}"</p>}
                  </div>
                  <StatusBadge status={doc.verification_status} />
                </li>
              ))}
            </ul>
          </Card>
        )}
      </div>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Submit document" description="We'll review it and update its status here.">
        <form onSubmit={submit} className="space-y-4">
          <Select label="Document type" value={documentType} onChange={(e) => setDocumentType(e.target.value)}>
            {DOCUMENT_TYPES.map((type) => (
              <option key={type} value={type}>
                {type.replace(/_/g, " ")}
              </option>
            ))}
          </Select>
          <Input
            label="Reference"
            value={reference}
            onChange={(e) => setReference(e.target.value)}
            placeholder="Document ID or reference number"
            required
          />
          <Input
            label="Expiry date"
            type="date"
            value={expiryDate}
            onChange={(e) => setExpiryDate(e.target.value)}
          />
          <Button type="submit" fullWidth isLoading={submitting}>
            Submit
          </Button>
        </form>
      </Modal>
    </DashboardLayout>
  );
}
