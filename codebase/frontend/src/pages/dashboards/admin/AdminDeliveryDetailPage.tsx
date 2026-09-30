import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, MapPin, RotateCcw, History } from "lucide-react";
import { DashboardLayout } from "../../../layouts/DashboardLayout";
import { Card, CardHeader, CardBody } from "../../../components/ui/Card";
import { Button } from "../../../components/ui/Button";
import { StatusBadge } from "../../../components/ui/Badge";
import { Alert } from "../../../components/ui/Alert";
import { useToast } from "../../../context/ToastContext";
import { logisticsService } from "../../../services/logisticsService";
import { extractApiErrorMessage } from "../../../services/apiClient";
import type { Delivery } from "../../../types/logistics";
import { SkeletonBlock } from "../../../components/ui/Skeleton";

const REASSIGNABLE_STATUSES = new Set(["CREATED", "SEARCHING", "OFFERED", "ASSIGNED"]);

export function AdminDeliveryDetailPage() {
  const { deliveryId } = useParams<{ deliveryId: string }>();
  const { showSuccess, showError } = useToast();
  const [delivery, setDelivery] = useState<Delivery | null>(null);
  const [loading, setLoading] = useState(true);
  const [reassigning, setReassigning] = useState(false);

  const load = () => {
    if (!deliveryId) return;
    setLoading(true);
    logisticsService
      .adminGetDelivery(deliveryId)
      .then(setDelivery)
      .catch(() => showError("Could not load this delivery."))
      .finally(() => setLoading(false));
  };

  useEffect(load, [deliveryId]); // eslint-disable-line react-hooks/exhaustive-deps

  const reassign = async () => {
    if (!deliveryId) return;
    if (!window.confirm("Reassign this delivery? The current rider (if any) will be freed and dispatch retried.")) return;
    setReassigning(true);
    try {
      await logisticsService.adminReassignDelivery(deliveryId, "Reassigned by admin");
      showSuccess("Delivery reassignment triggered.");
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not reassign this delivery."));
    } finally {
      setReassigning(false);
    }
  };

  if (loading) {
    return (
      <DashboardLayout>
        <SkeletonBlock className="h-64" />
      </DashboardLayout>
    );
  }

  if (!delivery) {
    return (
      <DashboardLayout>
        <p className="text-sm text-ink-soft">Delivery not found.</p>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <Link to="/admin/dashboard/deliveries" className="inline-flex items-center gap-1.5 text-sm text-ink-soft hover:text-ink">
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to deliveries
        </Link>

        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="font-display text-2xl font-semibold text-ink">{delivery.order_number ?? delivery.order_id}</h1>
            <p className="text-ink-soft mt-1">{delivery.branch_name ?? "Branch"}</p>
          </div>
          <StatusBadge status={delivery.status} />
        </div>

        {delivery.cancellation_reason && <Alert tone="danger">{delivery.cancellation_reason}</Alert>}

        <Card>
          <CardHeader className="font-medium text-ink">Assignment</CardHeader>
          <CardBody className="space-y-3">
            <p className="text-sm text-ink-soft">
              Rider: {delivery.rider_name ?? "Unassigned"}
            </p>
            <p className="text-sm text-ink-soft flex items-center gap-1.5">
              <MapPin className="h-3.5 w-3.5" />
              Pickup ({delivery.pickup_latitude.toFixed(4)}, {delivery.pickup_longitude.toFixed(4)}) - Drop-off (
              {delivery.destination_latitude.toFixed(4)}, {delivery.destination_longitude.toFixed(4)})
            </p>
            {REASSIGNABLE_STATUSES.has(delivery.status) && (
              <Button variant="secondary" size="sm" isLoading={reassigning} onClick={reassign}>
                <RotateCcw className="h-3.5 w-3.5" />
                Reassign / retry dispatch
              </Button>
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader className="flex items-center gap-2 font-medium text-ink">
            <History className="h-4 w-4 text-primary" />
            Status history
          </CardHeader>
          {!delivery.status_history || delivery.status_history.length === 0 ? (
            <CardBody>
              <p className="text-sm text-ink-soft">No history yet.</p>
            </CardBody>
          ) : (
            <ul className="divide-y divide-line">
              {delivery.status_history.map((entry, index) => (
                <li key={index} className="flex items-center justify-between gap-3 px-5 py-3">
                  <div>
                    <p className="text-sm text-ink">
                      {entry.from_status ?? "-"} &rarr; {entry.to_status}
                    </p>
                    {entry.reason && <p className="text-xs text-ink-soft mt-0.5">{entry.reason}</p>}
                  </div>
                  <p className="text-xs text-ink-soft shrink-0">{new Date(entry.created_at).toLocaleString()}</p>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </DashboardLayout>
  );
}
