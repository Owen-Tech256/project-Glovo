import { useEffect, useState, type FormEvent } from "react";
import { MapPin, Plus, Pencil, XCircle, Radar, Trash2 } from "lucide-react";
import { DashboardLayout } from "../../../layouts/DashboardLayout";
import { Card, CardBody } from "../../../components/ui/Card";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { Modal } from "../../../components/ui/Modal";
import { StatusBadge } from "../../../components/ui/Badge";
import { EmptyState } from "../../../components/ui/EmptyState";
import { useToast } from "../../../context/ToastContext";
import { vendorService } from "../../../services/vendorService";
import { extractApiErrorMessage } from "../../../services/apiClient";
import type { Branch, DeliveryZone } from "../../../types/catalog";
import { SkeletonList } from "../../../components/ui/Skeleton";

const emptyBranchForm = { name: "", address: "", latitude: "", longitude: "", phone: "" };
const emptyZoneForm = { name: "", center_latitude: "", center_longitude: "", radius_meters: "" };

export function BranchesPage() {
  const { showSuccess, showError } = useToast();
  const [branches, setBranches] = useState<Branch[]>([]);
  const [loading, setLoading] = useState(true);

  const [branchModalOpen, setBranchModalOpen] = useState(false);
  const [editingBranch, setEditingBranch] = useState<Branch | null>(null);
  const [branchForm, setBranchForm] = useState(emptyBranchForm);
  const [savingBranch, setSavingBranch] = useState(false);

  const [zoneModalBranch, setZoneModalBranch] = useState<Branch | null>(null);
  const [zones, setZones] = useState<DeliveryZone[]>([]);
  const [zonesLoading, setZonesLoading] = useState(false);
  const [zoneForm, setZoneForm] = useState(emptyZoneForm);
  const [savingZone, setSavingZone] = useState(false);

  const loadBranches = () => {
    setLoading(true);
    vendorService
      .listMyBranches()
      .then(setBranches)
      .catch(() => showError("Could not load your branches."))
      .finally(() => setLoading(false));
  };

  useEffect(loadBranches, [showError]);

  const openCreateBranch = () => {
    setEditingBranch(null);
    setBranchForm(emptyBranchForm);
    setBranchModalOpen(true);
  };

  const openEditBranch = (branch: Branch) => {
    setEditingBranch(branch);
    setBranchForm({
      name: branch.name,
      address: branch.address,
      latitude: String(branch.latitude),
      longitude: String(branch.longitude),
      phone: branch.phone ?? "",
    });
    setBranchModalOpen(true);
  };

  const submitBranch = async (event: FormEvent) => {
    event.preventDefault();
    setSavingBranch(true);
    try {
      const payload = {
        name: branchForm.name,
        address: branchForm.address,
        latitude: Number(branchForm.latitude),
        longitude: Number(branchForm.longitude),
        phone: branchForm.phone || null,
      };
      if (editingBranch) {
        await vendorService.updateBranch(editingBranch.id, payload);
        showSuccess("Branch updated.");
      } else {
        await vendorService.createBranch(payload);
        showSuccess("Branch created.");
      }
      setBranchModalOpen(false);
      loadBranches();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not save this branch."));
    } finally {
      setSavingBranch(false);
    }
  };

  const closeBranch = async (branch: Branch) => {
    if (!window.confirm(`Close ${branch.name}? It will no longer be visible to customers.`)) return;
    try {
      await vendorService.closeBranch(branch.id);
      showSuccess("Branch closed.");
      loadBranches();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not close this branch."));
    }
  };

  const openZones = (branch: Branch) => {
    setZoneModalBranch(branch);
    setZoneForm(emptyZoneForm);
    setZonesLoading(true);
    vendorService
      .listZones(branch.id)
      .then(setZones)
      .catch(() => showError("Could not load delivery zones."))
      .finally(() => setZonesLoading(false));
  };

  const submitZone = async (event: FormEvent) => {
    event.preventDefault();
    if (!zoneModalBranch) return;
    setSavingZone(true);
    try {
      const zone = await vendorService.createZone(zoneModalBranch.id, {
        name: zoneForm.name,
        center_latitude: Number(zoneForm.center_latitude),
        center_longitude: Number(zoneForm.center_longitude),
        radius_meters: Number(zoneForm.radius_meters),
      });
      setZones((current) => [zone, ...current]);
      setZoneForm(emptyZoneForm);
      showSuccess("Delivery zone added.");
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not create this delivery zone."));
    } finally {
      setSavingZone(false);
    }
  };

  const toggleZoneStatus = async (zone: DeliveryZone) => {
    if (!zoneModalBranch) return;
    try {
      const updated = await vendorService.updateZone(zoneModalBranch.id, zone.id, {
        status: zone.status === "ACTIVE" ? "INACTIVE" : "ACTIVE",
      });
      setZones((current) => current.map((z) => (z.id === zone.id ? updated : z)));
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not update this delivery zone."));
    }
  };

  const removeZone = async (zone: DeliveryZone) => {
    if (!zoneModalBranch) return;
    if (!window.confirm(`Delete the "${zone.name}" delivery zone?`)) return;
    try {
      await vendorService.deleteZone(zoneModalBranch.id, zone.id);
      setZones((current) => current.filter((z) => z.id !== zone.id));
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not delete this delivery zone."));
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="font-display text-2xl font-semibold text-ink">Branches</h1>
            <p className="text-ink-soft mt-1">Manage your locations and where each one delivers.</p>
          </div>
          <Button onClick={openCreateBranch}>
            <Plus className="h-4 w-4" />
            Add branch
          </Button>
        </div>

        {loading ? (
          <SkeletonList />
        ) : branches.length === 0 ? (
          <EmptyState
            icon={<MapPin className="h-5 w-5" />}
            title="No branches yet"
            description="Add your first location so customers can find you and place orders."
          />
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {branches.map((branch) => (
              <Card key={branch.id}>
                <CardBody className="space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="font-medium text-ink">{branch.name}</p>
                      <p className="text-sm text-ink-soft mt-0.5">{branch.address}</p>
                    </div>
                    <StatusBadge status={branch.status} />
                  </div>
                  {branch.phone && <p className="text-sm text-ink-soft">{branch.phone}</p>}
                  <div className="flex flex-wrap items-center gap-2 pt-1">
                    <Button variant="secondary" size="sm" onClick={() => openEditBranch(branch)}>
                      <Pencil className="h-3.5 w-3.5" />
                      Edit
                    </Button>
                    <Button variant="secondary" size="sm" onClick={() => openZones(branch)}>
                      <Radar className="h-3.5 w-3.5" />
                      Delivery zones
                    </Button>
                    {branch.status !== "CLOSED" && (
                      <Button variant="ghost" size="sm" onClick={() => closeBranch(branch)}>
                        <XCircle className="h-3.5 w-3.5" />
                        Close
                      </Button>
                    )}
                  </div>
                </CardBody>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Create / edit branch */}
      <Modal
        open={branchModalOpen}
        onClose={() => setBranchModalOpen(false)}
        title={editingBranch ? "Edit branch" : "Add branch"}
        description="Coordinates are used to determine which delivery zones cover this location."
      >
        <form onSubmit={submitBranch} className="space-y-4">
          <Input
            label="Branch name"
            value={branchForm.name}
            onChange={(e) => setBranchForm({ ...branchForm, name: e.target.value })}
            required
          />
          <Input
            label="Address"
            value={branchForm.address}
            onChange={(e) => setBranchForm({ ...branchForm, address: e.target.value })}
            required
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Latitude"
              type="number"
              step="any"
              value={branchForm.latitude}
              onChange={(e) => setBranchForm({ ...branchForm, latitude: e.target.value })}
              required
            />
            <Input
              label="Longitude"
              type="number"
              step="any"
              value={branchForm.longitude}
              onChange={(e) => setBranchForm({ ...branchForm, longitude: e.target.value })}
              required
            />
          </div>
          <Input
            label="Phone"
            value={branchForm.phone}
            onChange={(e) => setBranchForm({ ...branchForm, phone: e.target.value })}
            placeholder="+1 202 555 0123"
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="secondary" onClick={() => setBranchModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={savingBranch}>
              {editingBranch ? "Save changes" : "Create branch"}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Delivery zones */}
      <Modal
        open={Boolean(zoneModalBranch)}
        onClose={() => setZoneModalBranch(null)}
        title={`Delivery zones - ${zoneModalBranch?.name ?? ""}`}
        description="A radius-based area around a center point. Customers inside an active zone can discover this branch."
        size="lg"
      >
        <div className="space-y-5">
          <form onSubmit={submitZone} className="grid sm:grid-cols-2 gap-3 rounded-md border border-line p-3">
            <div className="sm:col-span-2">
              <Input
                label="Zone name"
                value={zoneForm.name}
                onChange={(e) => setZoneForm({ ...zoneForm, name: e.target.value })}
                placeholder="e.g. 5km delivery radius"
                required
              />
            </div>
            <Input
              label="Center latitude"
              type="number"
              step="any"
              value={zoneForm.center_latitude}
              onChange={(e) => setZoneForm({ ...zoneForm, center_latitude: e.target.value })}
              required
            />
            <Input
              label="Center longitude"
              type="number"
              step="any"
              value={zoneForm.center_longitude}
              onChange={(e) => setZoneForm({ ...zoneForm, center_longitude: e.target.value })}
              required
            />
            <Input
              label="Radius (meters)"
              type="number"
              min="1"
              value={zoneForm.radius_meters}
              onChange={(e) => setZoneForm({ ...zoneForm, radius_meters: e.target.value })}
              required
            />
            <div className="flex items-end">
              <Button type="submit" size="sm" isLoading={savingZone} fullWidth>
                <Plus className="h-3.5 w-3.5" />
                Add zone
              </Button>
            </div>
          </form>

          {zonesLoading ? (
            <SkeletonList rows={3} />
          ) : zones.length === 0 ? (
            <p className="text-sm text-ink-soft">No delivery zones yet - this branch won't appear in customer search.</p>
          ) : (
            <ul className="divide-y divide-line rounded-md border border-line">
              {zones.map((zone) => (
                <li key={zone.id} className="flex items-center justify-between gap-3 px-3 py-2.5">
                  <div>
                    <p className="text-sm font-medium text-ink">{zone.name}</p>
                    <p className="text-xs text-ink-soft">
                      {zone.radius_meters ? `${(zone.radius_meters / 1000).toFixed(1)} km radius` : "-"} around (
                      {zone.center_latitude}, {zone.center_longitude})
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <StatusBadge status={zone.status} />
                    <Button variant="ghost" size="sm" onClick={() => toggleZoneStatus(zone)}>
                      {zone.status === "ACTIVE" ? "Deactivate" : "Activate"}
                    </Button>
                    <button
                      onClick={() => removeZone(zone)}
                      aria-label="Delete zone"
                      className="text-ink-soft hover:text-danger p-1.5 rounded-md hover:bg-danger-soft"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </Modal>
    </DashboardLayout>
  );
}
