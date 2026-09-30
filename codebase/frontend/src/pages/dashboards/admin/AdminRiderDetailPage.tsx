import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Bike, FileCheck, Truck, CheckCircle2, Ban } from "lucide-react";
import { DashboardLayout } from "../../../layouts/DashboardLayout";
import { Card, CardHeader, CardBody } from "../../../components/ui/Card";
import { Button } from "../../../components/ui/Button";
import { StatusBadge } from "../../../components/ui/Badge";
import { useToast } from "../../../context/ToastContext";
import { logisticsService } from "../../../services/logisticsService";
import { extractApiErrorMessage } from "../../../services/apiClient";
import type { Rider, RiderDocument, RiderOnboardingStatus } from "../../../types/logistics";
import { SkeletonBlock } from "../../../components/ui/Skeleton";

// Mirrors the backend's _ONBOARDING_TRANSITIONS table so the UI only ever
// offers a rider status change the API will actually accept.
const NEXT_STATUSES: Record<RiderOnboardingStatus, RiderOnboardingStatus[]> = {
  PENDING: ["UNDER_REVIEW", "REJECTED"],
  UNDER_REVIEW: ["APPROVED", "REJECTED"],
  APPROVED: ["SUSPENDED"],
  REJECTED: ["UNDER_REVIEW"],
  SUSPENDED: ["APPROVED", "REJECTED"],
};

export function AdminRiderDetailPage() {
  const { riderId } = useParams<{ riderId: string }>();
  const { showSuccess, showError } = useToast();
  const [rider, setRider] = useState<Rider | null>(null);
  const [documents, setDocuments] = useState<RiderDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [actingStatus, setActingStatus] = useState<string | null>(null);
  const [reviewingId, setReviewingId] = useState<string | null>(null);

  const load = () => {
    if (!riderId) return;
    setLoading(true);
    Promise.all([logisticsService.adminGetRider(riderId), logisticsService.adminListRiderDocuments(riderId)])
      .then(([riderData, docs]) => {
        setRider(riderData);
        setDocuments(docs);
      })
      .catch(() => showError("Could not load this rider."))
      .finally(() => setLoading(false));
  };

  useEffect(load, [riderId]); // eslint-disable-line react-hooks/exhaustive-deps

  const changeStatus = async (status: RiderOnboardingStatus) => {
    if (!riderId) return;
    setActingStatus(status);
    try {
      await logisticsService.adminSetRiderStatus(riderId, status);
      showSuccess(`Rider ${status.toLowerCase().replace(/_/g, " ")}.`);
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not update rider status."));
    } finally {
      setActingStatus(null);
    }
  };

  const reviewDocument = async (document: RiderDocument, verification_status: "VERIFIED" | "REJECTED") => {
    if (!riderId) return;
    setReviewingId(document.id);
    try {
      await logisticsService.adminReviewDocument(riderId, document.id, verification_status);
      showSuccess(`Document ${verification_status.toLowerCase()}.`);
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not review this document."));
    } finally {
      setReviewingId(null);
    }
  };

  if (loading) {
    return (
      <DashboardLayout>
        <SkeletonBlock className="h-64" />
      </DashboardLayout>
    );
  }

  if (!rider) {
    return (
      <DashboardLayout>
        <p className="text-sm text-ink-soft">Rider not found.</p>
      </DashboardLayout>
    );
  }

  const nextStatuses = NEXT_STATUSES[rider.onboarding_status] ?? [];

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <Link to="/admin/dashboard/riders" className="inline-flex items-center gap-1.5 text-sm text-ink-soft hover:text-ink">
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to riders
        </Link>

        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="font-display text-2xl font-semibold text-ink">{rider.full_name ?? rider.id}</h1>
            <p className="text-ink-soft mt-1">Rider since {new Date(rider.created_at).toLocaleDateString()}</p>
          </div>
          <div className="flex items-center gap-2">
            <StatusBadge status={rider.operational_status} />
            <StatusBadge status={rider.onboarding_status} />
          </div>
        </div>

        <Card>
          <CardHeader className="flex items-center gap-2 font-medium text-ink">
            <Bike className="h-4 w-4 text-primary" />
            Onboarding
          </CardHeader>
          <CardBody className="flex flex-wrap gap-2">
            {nextStatuses.length === 0 ? (
              <p className="text-sm text-ink-soft">No further transitions available.</p>
            ) : (
              nextStatuses.map((status) => (
                <Button
                  key={status}
                  variant={status === "REJECTED" || status === "SUSPENDED" ? "danger" : "primary"}
                  size="sm"
                  isLoading={actingStatus === status}
                  onClick={() => changeStatus(status)}
                >
                  {status === "APPROVED" ? <CheckCircle2 className="h-3.5 w-3.5" /> : status === "REJECTED" || status === "SUSPENDED" ? <Ban className="h-3.5 w-3.5" /> : null}
                  {status.replace(/_/g, " ").toLowerCase()}
                </Button>
              ))
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader className="flex items-center gap-2 font-medium text-ink">
            <Truck className="h-4 w-4 text-primary" />
            Vehicle
          </CardHeader>
          <CardBody>
            {rider.vehicle ? (
              <p className="text-sm text-ink-soft">
                {rider.vehicle.vehicle_type.replace(/_/g, " ").toLowerCase()}
                {rider.vehicle.registration_reference ? ` - ${rider.vehicle.registration_reference}` : ""}
              </p>
            ) : (
              <p className="text-sm text-ink-soft">No vehicle on file yet.</p>
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader className="flex items-center gap-2 font-medium text-ink">
            <FileCheck className="h-4 w-4 text-primary" />
            Documents ({documents.length})
          </CardHeader>
          {documents.length === 0 ? (
            <CardBody>
              <p className="text-sm text-ink-soft">No documents submitted yet.</p>
            </CardBody>
          ) : (
            <ul className="divide-y divide-line">
              {documents.map((doc) => (
                <li key={doc.id} className="flex items-center justify-between gap-3 px-5 py-3.5">
                  <div>
                    <p className="text-sm font-medium text-ink">{doc.document_type.replace(/_/g, " ")}</p>
                    <p className="text-xs text-ink-soft mt-0.5">
                      {doc.reference}
                      {doc.expiry_date ? ` - expires ${doc.expiry_date}` : ""}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <StatusBadge status={doc.verification_status} />
                    {doc.verification_status === "PENDING" && (
                      <>
                        <Button
                          variant="ghost"
                          size="sm"
                          isLoading={reviewingId === doc.id}
                          onClick={() => reviewDocument(doc, "REJECTED")}
                        >
                          Reject
                        </Button>
                        <Button size="sm" isLoading={reviewingId === doc.id} onClick={() => reviewDocument(doc, "VERIFIED")}>
                          Verify
                        </Button>
                      </>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </DashboardLayout>
  );
}
