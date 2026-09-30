import { type FormEvent, useEffect, useState } from "react";
import { Truck } from "lucide-react";
import { DashboardLayout } from "../../../layouts/DashboardLayout";
import { Card, CardBody } from "../../../components/ui/Card";
import { Button } from "../../../components/ui/Button";
import { Select } from "../../../components/ui/Select";
import { Input } from "../../../components/ui/Input";
import { useToast } from "../../../context/ToastContext";
import { logisticsService } from "../../../services/logisticsService";
import { extractApiErrorMessage } from "../../../services/apiClient";
import type { Rider } from "../../../types/logistics";
import { SkeletonBlock } from "../../../components/ui/Skeleton";

const VEHICLE_TYPES = ["BICYCLE", "SCOOTER", "MOTORCYCLE", "CAR", "ON_FOOT"];

export function VehiclePage() {
  const { showSuccess, showError } = useToast();
  const [rider, setRider] = useState<Rider | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [vehicleType, setVehicleType] = useState("BICYCLE");
  const [registrationReference, setRegistrationReference] = useState("");

  useEffect(() => {
    logisticsService
      .getMe()
      .then((data) => {
        setRider(data);
        if (data.vehicle) {
          setVehicleType(data.vehicle.vehicle_type);
          setRegistrationReference(data.vehicle.registration_reference ?? "");
        }
      })
      .catch(() => showError("Could not load your vehicle profile."))
      .finally(() => setLoading(false));
  }, [showError]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    try {
      const updated = await logisticsService.updateProfile({
        vehicle_type: vehicleType,
        registration_reference: registrationReference || null,
      });
      setRider(updated);
      showSuccess("Vehicle profile saved.");
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not save your vehicle profile."));
    } finally {
      setSaving(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="max-w-xl space-y-6">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink">Vehicle</h1>
          <p className="text-ink-soft mt-1">Tell us what you'll be delivering on.</p>
        </div>

        {loading ? (
          <SkeletonBlock className="h-64" />
        ) : (
          <Card>
            <CardBody>
              <form onSubmit={submit} className="space-y-4">
                <Select label="Vehicle type" value={vehicleType} onChange={(e) => setVehicleType(e.target.value)}>
                  {VEHICLE_TYPES.map((type) => (
                    <option key={type} value={type}>
                      {type.replace(/_/g, " ")}
                    </option>
                  ))}
                </Select>
                <Input
                  label="Registration reference"
                  icon={<Truck className="h-4 w-4" />}
                  value={registrationReference}
                  onChange={(e) => setRegistrationReference(e.target.value)}
                  placeholder="Plate number, if applicable"
                />
                <Button type="submit" isLoading={saving}>
                  Save vehicle
                </Button>
              </form>
            </CardBody>
          </Card>
        )}

        {rider?.vehicle && (
          <p className="text-xs text-ink-soft">Last updated {new Date(rider.vehicle.updated_at).toLocaleString()}</p>
        )}
      </div>
    </DashboardLayout>
  );
}
