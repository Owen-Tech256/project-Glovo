import { useCallback, useEffect, useRef, useState } from "react";
import { Bike, Clock, MapPin, Navigation, PackageCheck, Truck } from "lucide-react";
import { DashboardLayout } from "../../../layouts/DashboardLayout";
import { Card, CardBody, CardHeader } from "../../../components/ui/Card";
import { Button } from "../../../components/ui/Button";
import { StatusBadge } from "../../../components/ui/Badge";
import { Alert } from "../../../components/ui/Alert";
import { EmptyState } from "../../../components/ui/EmptyState";
import { useToast } from "../../../context/ToastContext";
import { logisticsService } from "../../../services/logisticsService";
import { extractApiErrorMessage } from "../../../services/apiClient";
import type { Delivery, DeliveryOffer } from "../../../types/logistics";
import { SkeletonList } from "../../../components/ui/Skeleton";

const OFFERS_POLL_MS = 8000;

export function DeliveriesPage() {
  const { showSuccess, showError } = useToast();
  const [currentDelivery, setCurrentDelivery] = useState<Delivery | null>(null);
  const [offers, setOffers] = useState<DeliveryOffer[]>([]);
  const [loading, setLoading] = useState(true);
  const [actingId, setActingId] = useState<string | null>(null);
  const [sharingLocation, setSharingLocation] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(async () => {
    try {
      const delivery = await logisticsService.getCurrentDelivery();
      setCurrentDelivery(delivery);
      if (!delivery) {
        setOffers(await logisticsService.listOffers());
      } else {
        setOffers([]);
      }
    } catch {
      showError("Could not load your deliveries.");
    } finally {
      setLoading(false);
    }
  }, [showError]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (currentDelivery) {
      if (pollRef.current) clearInterval(pollRef.current);
      return;
    }
    pollRef.current = setInterval(load, OFFERS_POLL_MS);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [currentDelivery, load]);

  const shareLocation = () => {
    if (!navigator.geolocation) {
      showError("Location isn't available in this browser.");
      return;
    }
    setSharingLocation(true);
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        try {
          await logisticsService.postLocation(
            position.coords.latitude,
            position.coords.longitude,
            position.coords.accuracy
          );
          showSuccess("Location shared.");
          load();
        } catch (error) {
          showError(extractApiErrorMessage(error, "Could not share your location."));
        } finally {
          setSharingLocation(false);
        }
      },
      () => {
        showError("Could not access your location.");
        setSharingLocation(false);
      }
    );
  };

  const acceptOffer = async (offer: DeliveryOffer) => {
    setActingId(offer.id);
    try {
      const delivery = await logisticsService.acceptOffer(offer.id);
      setCurrentDelivery(delivery);
      setOffers([]);
      showSuccess("Delivery accepted.");
    } catch (error) {
      showError(extractApiErrorMessage(error, "This offer is no longer available."));
      load();
    } finally {
      setActingId(null);
    }
  };

  const rejectOffer = async (offer: DeliveryOffer) => {
    setActingId(offer.id);
    try {
      await logisticsService.rejectOffer(offer.id);
      showSuccess("Offer declined.");
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not decline this offer."));
    } finally {
      setActingId(null);
    }
  };

  const advanceDelivery = async (action: "pickup" | "start" | "complete") => {
    if (!currentDelivery) return;
    setActingId(currentDelivery.id);
    try {
      const updated =
        action === "pickup"
          ? await logisticsService.pickup(currentDelivery.id)
          : action === "start"
          ? await logisticsService.startDelivering(currentDelivery.id)
          : await logisticsService.complete(currentDelivery.id);
      setCurrentDelivery(updated.status === "DELIVERED" ? null : updated);
      showSuccess(
        action === "pickup" ? "Marked as picked up." : action === "start" ? "Delivery in progress." : "Delivery completed."
      );
      if (updated.status === "DELIVERED") load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not update this delivery."));
    } finally {
      setActingId(null);
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6 max-w-2xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="font-display text-2xl font-semibold text-ink">Deliveries</h1>
            <p className="text-ink-soft mt-1">Accept jobs, pick up, and deliver orders.</p>
          </div>
          <Button variant="secondary" size="sm" isLoading={sharingLocation} onClick={shareLocation}>
            <Navigation className="h-3.5 w-3.5" />
            Share location
          </Button>
        </div>

        {loading ? (
          <SkeletonList />
        ) : currentDelivery ? (
          <Card>
            <CardHeader className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Bike className="h-4 w-4 text-ink-soft" />
                <h2 className="font-medium text-ink text-sm">{currentDelivery.order_number ?? currentDelivery.order_id}</h2>
              </div>
              <StatusBadge status={currentDelivery.status} />
            </CardHeader>
            <CardBody className="space-y-4">
              <div className="text-sm text-ink-soft space-y-1.5">
                <p className="flex items-center gap-2">
                  <MapPin className="h-3.5 w-3.5 shrink-0" />
                  Pickup: {currentDelivery.branch_name ?? "Branch"} ({currentDelivery.pickup_latitude.toFixed(4)},{" "}
                  {currentDelivery.pickup_longitude.toFixed(4)})
                </p>
                <p className="flex items-center gap-2">
                  <MapPin className="h-3.5 w-3.5 shrink-0" />
                  Drop-off: ({currentDelivery.destination_latitude.toFixed(4)}, {currentDelivery.destination_longitude.toFixed(4)})
                </p>
              </div>

              {currentDelivery.status === "ASSIGNED" && (
                <Button fullWidth isLoading={actingId === currentDelivery.id} onClick={() => advanceDelivery("pickup")}>
                  <PackageCheck className="h-4 w-4" />
                  Mark picked up
                </Button>
              )}
              {currentDelivery.status === "PICKED_UP" && (
                <Button fullWidth isLoading={actingId === currentDelivery.id} onClick={() => advanceDelivery("start")}>
                  <Truck className="h-4 w-4" />
                  Start delivering
                </Button>
              )}
              {currentDelivery.status === "DELIVERING" && (
                <Button fullWidth isLoading={actingId === currentDelivery.id} onClick={() => advanceDelivery("complete")}>
                  <PackageCheck className="h-4 w-4" />
                  Mark delivered
                </Button>
              )}
            </CardBody>
          </Card>
        ) : offers.length === 0 ? (
          <EmptyState
            icon={<Bike className="h-5 w-5" />}
            title="No delivery offers"
            description="Go online and share your location to start receiving offers."
          />
        ) : (
          <div className="space-y-3">
            <Alert tone="info">You have {offers.length} pending delivery offer{offers.length > 1 ? "s" : ""}.</Alert>
            {offers.map((offer) => (
              <Card key={offer.id}>
                <CardBody className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-sm font-medium text-ink">New delivery offer</p>
                    <p className="text-xs text-ink-soft mt-0.5 flex items-center gap-1.5">
                      <Clock className="h-3 w-3" />
                      Expires {new Date(offer.expires_at).toLocaleTimeString()}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <Button
                      variant="secondary"
                      size="sm"
                      isLoading={actingId === offer.id}
                      onClick={() => rejectOffer(offer)}
                    >
                      Decline
                    </Button>
                    <Button size="sm" isLoading={actingId === offer.id} onClick={() => acceptOffer(offer)}>
                      Accept
                    </Button>
                  </div>
                </CardBody>
              </Card>
            ))}
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
