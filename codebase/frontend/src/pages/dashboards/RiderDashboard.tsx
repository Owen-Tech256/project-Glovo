import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bike, FileCheck, MapPin, Truck, Navigation } from "lucide-react";
import { DashboardLayout } from "../../layouts/DashboardLayout";
import { AccountSummaryCard } from "../../components/AccountSummaryCard";
import { Card, CardBody, CardHeader } from "../../components/ui/Card";
import { StatusBadge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Alert } from "../../components/ui/Alert";
import { useAuth } from "../../context/AuthContext";
import { useToast } from "../../context/ToastContext";
import { logisticsService } from "../../services/logisticsService";
import { extractApiErrorMessage } from "../../services/apiClient";
import type { Rider, Delivery } from "../../types/logistics";
import { SkeletonList } from "../../components/ui/Skeleton";

const onboardingCopy: Record<string, { tone: "info" | "success" | "danger"; message: string }> = {
  PENDING: { tone: "info", message: "Submit your vehicle details and documents to start the verification process." },
  UNDER_REVIEW: { tone: "info", message: "Your application is under review. We'll notify you once it's decided." },
  APPROVED: { tone: "success", message: "You're approved to deliver. Go available to start receiving offers." },
  REJECTED: { tone: "danger", message: "Your application was rejected. Contact support for more information." },
  SUSPENDED: { tone: "danger", message: "Your account is suspended and cannot go online right now." },
};

export function RiderDashboard() {
  const { user } = useAuth();
  const { showSuccess, showError } = useToast();
  const [rider, setRider] = useState<Rider | null>(null);
  const [currentDelivery, setCurrentDelivery] = useState<Delivery | null>(null);
  const [loading, setLoading] = useState(true);
  const [togglingAvailability, setTogglingAvailability] = useState(false);

  const load = () => {
    setLoading(true);
    Promise.all([logisticsService.getMe(), logisticsService.getCurrentDelivery()])
      .then(([riderData, delivery]) => {
        setRider(riderData);
        setCurrentDelivery(delivery);
      })
      .catch(() => showError("Could not load your rider profile."))
      .finally(() => setLoading(false));
  };

  useEffect(load, [showError]);

  const toggleAvailability = async () => {
    if (!rider) return;
    const next = rider.operational_status === "OFFLINE" ? "AVAILABLE" : "OFFLINE";
    setTogglingAvailability(true);
    try {
      const updated = await logisticsService.setAvailability(next);
      setRider(updated);
      showSuccess(next === "AVAILABLE" ? "You're online." : "You're offline.");
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not update your availability."));
    } finally {
      setTogglingAvailability(false);
    }
  };

  if (!user) return null;

  const onboarding = rider ? onboardingCopy[rider.onboarding_status] : null;

  return (
    <DashboardLayout>
      <div className="space-y-8">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink">Welcome, {user.full_name.split(" ")[0]}</h1>
          <p className="text-ink-soft mt-1">Manage your availability and active deliveries.</p>
        </div>

        {!loading && onboarding && rider && rider.onboarding_status !== "APPROVED" && (
          <Alert tone={onboarding.tone}>{onboarding.message}</Alert>
        )}

        <div className="grid lg:grid-cols-3 gap-4">
          <div className="lg:col-span-1 space-y-4">
            <AccountSummaryCard user={user} />
            <Card>
              <CardBody className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-ink text-sm mb-0.5">Availability</p>
                  <p className="text-xs text-ink-soft">
                    {rider?.onboarding_status === "APPROVED"
                      ? "Toggle to start receiving delivery offers."
                      : "Available once your onboarding is approved."}
                  </p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <StatusBadge status={rider?.operational_status ?? "OFFLINE"} />
                  {rider?.operational_status !== "BUSY" && (
                    <Button
                      size="sm"
                      variant={rider?.operational_status === "AVAILABLE" ? "secondary" : "primary"}
                      isLoading={togglingAvailability}
                      disabled={!rider || rider.onboarding_status !== "APPROVED"}
                      onClick={toggleAvailability}
                    >
                      {rider?.operational_status === "AVAILABLE" ? "Go offline" : "Go online"}
                    </Button>
                  )}
                </div>
              </CardBody>
            </Card>
            <Card>
              <CardBody>
                <p className="font-medium text-ink text-sm mb-0.5">Onboarding status</p>
                <StatusBadge status={rider?.onboarding_status ?? "PENDING"} />
              </CardBody>
            </Card>
          </div>

          <div className="lg:col-span-2 space-y-4">
            <Card>
              <CardHeader className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Bike className="h-4 w-4 text-ink-soft" />
                  <h2 className="font-medium text-ink text-sm">Current delivery</h2>
                </div>
                <Link to="/rider/dashboard/deliveries" className="text-xs font-medium text-primary hover:underline">
                  View deliveries
                </Link>
              </CardHeader>
              <CardBody>
                {loading ? (
                  <SkeletonList />
                ) : currentDelivery ? (
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-ink">{currentDelivery.order_number ?? currentDelivery.order_id}</p>
                      <p className="text-xs text-ink-soft mt-0.5">{currentDelivery.branch_name}</p>
                    </div>
                    <StatusBadge status={currentDelivery.status} />
                  </div>
                ) : (
                  <p className="text-sm text-ink-soft">No active delivery right now.</p>
                )}
              </CardBody>
            </Card>

            <div className="grid sm:grid-cols-3 gap-4">
              <Link to="/rider/dashboard/vehicle">
                <Card className="h-full hover:border-ink transition-colors">
                  <CardBody className="flex items-start gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-md bg-ink/[0.04] text-ink-soft shrink-0">
                      <Truck className="h-4.5 w-4.5" />
                    </div>
                    <div>
                      <p className="font-medium text-ink text-sm">Vehicle</p>
                      <p className="text-xs text-ink-soft mt-0.5">
                        {rider?.vehicle ? rider.vehicle.vehicle_type.replace(/_/g, " ").toLowerCase() : "Not set up yet"}
                      </p>
                    </div>
                  </CardBody>
                </Card>
              </Link>
              <Link to="/rider/dashboard/documents">
                <Card className="h-full hover:border-ink transition-colors">
                  <CardBody className="flex items-start gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-md bg-ink/[0.04] text-ink-soft shrink-0">
                      <FileCheck className="h-4.5 w-4.5" />
                    </div>
                    <div>
                      <p className="font-medium text-ink text-sm">Documents</p>
                      <p className="text-xs text-ink-soft mt-0.5">Submit verification documents</p>
                    </div>
                  </CardBody>
                </Card>
              </Link>
              <Link to="/rider/dashboard/zones">
                <Card className="h-full hover:border-ink transition-colors">
                  <CardBody className="flex items-start gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-md bg-ink/[0.04] text-ink-soft shrink-0">
                      <MapPin className="h-4.5 w-4.5" />
                    </div>
                    <div>
                      <p className="font-medium text-ink text-sm">Zones</p>
                      <p className="text-xs text-ink-soft mt-0.5">Where you accept deliveries</p>
                    </div>
                  </CardBody>
                </Card>
              </Link>
            </div>

            {rider?.location_updated_at && (
              <Card>
                <CardBody className="flex items-center gap-2 text-xs text-ink-soft">
                  <Navigation className="h-3.5 w-3.5" />
                  Last location update: {new Date(rider.location_updated_at).toLocaleString()}
                </CardBody>
              </Card>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
