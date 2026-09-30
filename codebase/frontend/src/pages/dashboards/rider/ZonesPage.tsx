import { type FormEvent, useEffect, useState } from "react";
import { MapPin, Plus, Trash2 } from "lucide-react";
import { DashboardLayout } from "../../../layouts/DashboardLayout";
import { Card, CardBody } from "../../../components/ui/Card";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { Alert } from "../../../components/ui/Alert";
import { EmptyState } from "../../../components/ui/EmptyState";
import { useToast } from "../../../context/ToastContext";
import { logisticsService } from "../../../services/logisticsService";
import { extractApiErrorMessage } from "../../../services/apiClient";
import type { RiderZone } from "../../../types/logistics";
import { SkeletonList } from "../../../components/ui/Skeleton";

export function ZonesPage() {
  const { showSuccess, showError } = useToast();
  const [zones, setZones] = useState<RiderZone[]>([]);
  const [loading, setLoading] = useState(true);
  const [zoneId, setZoneId] = useState("");
  const [joining, setJoining] = useState(false);
  const [leavingId, setLeavingId] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    logisticsService
      .listZones()
      .then(setZones)
      .catch(() => showError("Could not load your zones."))
      .finally(() => setLoading(false));
  };

  useEffect(load, [showError]);

  const join = async (event: FormEvent) => {
    event.preventDefault();
    setJoining(true);
    try {
      await logisticsService.joinZone(zoneId.trim());
      showSuccess("Zone added.");
      setZoneId("");
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not add this zone."));
    } finally {
      setJoining(false);
    }
  };

  const leave = async (zone: RiderZone) => {
    setLeavingId(zone.id);
    try {
      await logisticsService.leaveZone(zone.zone_id);
      showSuccess("Zone removed.");
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not remove this zone."));
    } finally {
      setLeavingId(null);
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6 max-w-xl">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink">Operating zones</h1>
          <p className="text-ink-soft mt-1">You'll only receive delivery offers for zones you've joined.</p>
        </div>

        <Card>
          <CardBody>
            <form onSubmit={join} className="flex items-end gap-3">
              <div className="flex-1">
                <Input
                  label="Zone ID"
                  value={zoneId}
                  onChange={(e) => setZoneId(e.target.value)}
                  placeholder="Ask a vendor or admin for a zone ID"
                  required
                />
              </div>
              <Button type="submit" isLoading={joining}>
                <Plus className="h-4 w-4" />
                Join
              </Button>
            </form>
          </CardBody>
        </Card>

        <Alert tone="info">Zone IDs are shared by vendors or admins for the areas they operate in.</Alert>

        {loading ? (
          <SkeletonList />
        ) : zones.length === 0 ? (
          <EmptyState icon={<MapPin className="h-5 w-5" />} title="No zones yet" description="Join a zone to start receiving offers there." />
        ) : (
          <Card>
            <ul className="divide-y divide-line">
              {zones.map((zone) => (
                <li key={zone.id} className="flex items-center justify-between gap-3 px-5 py-3.5">
                  <div>
                    <p className="font-medium text-ink text-sm">{zone.zone_name ?? zone.zone_id}</p>
                    {zone.branch_name && <p className="text-xs text-ink-soft mt-0.5">{zone.branch_name}</p>}
                  </div>
                  <Button variant="ghost" size="sm" isLoading={leavingId === zone.id} onClick={() => leave(zone)}>
                    <Trash2 className="h-3.5 w-3.5" />
                    Leave
                  </Button>
                </li>
              ))}
            </ul>
          </Card>
        )}
      </div>
    </DashboardLayout>
  );
}
