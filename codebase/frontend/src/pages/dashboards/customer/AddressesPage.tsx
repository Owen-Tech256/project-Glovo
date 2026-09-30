import { useEffect, useState, type FormEvent } from "react";
import { MapPin, Plus, Pencil, Trash2, Star } from "lucide-react";
import { DashboardLayout } from "../../../layouts/DashboardLayout";
import { Card, CardBody } from "../../../components/ui/Card";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { Textarea } from "../../../components/ui/Textarea";
import { Modal } from "../../../components/ui/Modal";
import { Badge } from "../../../components/ui/Badge";
import { EmptyState } from "../../../components/ui/EmptyState";
import { useToast } from "../../../context/ToastContext";
import { addressService, type AddressInput } from "../../../services/addressService";
import { extractApiErrorMessage } from "../../../services/apiClient";
import type { CustomerAddress } from "../../../types/catalog";
import { SkeletonList } from "../../../components/ui/Skeleton";

const emptyForm = {
  label: "",
  recipient_name: "",
  phone: "",
  address_line1: "",
  address_line2: "",
  city: "",
  state: "",
  postal_code: "",
  country: "",
  latitude: "",
  longitude: "",
  delivery_instructions: "",
};

export function AddressesPage() {
  const { showSuccess, showError } = useToast();
  const [addresses, setAddresses] = useState<CustomerAddress[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<CustomerAddress | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);

  const load = () => {
    setLoading(true);
    addressService
      .list()
      .then(setAddresses)
      .catch(() => showError("Could not load your addresses."))
      .finally(() => setLoading(false));
  };

  useEffect(load, [showError]);

  const openCreate = () => {
    setEditing(null);
    setForm(emptyForm);
    setModalOpen(true);
  };

  const openEdit = (address: CustomerAddress) => {
    setEditing(address);
    setForm({
      label: address.label,
      recipient_name: address.recipient_name,
      phone: address.phone,
      address_line1: address.address_line1,
      address_line2: address.address_line2 ?? "",
      city: address.city,
      state: address.state ?? "",
      postal_code: address.postal_code ?? "",
      country: address.country,
      latitude: String(address.latitude),
      longitude: String(address.longitude),
      delivery_instructions: address.delivery_instructions ?? "",
    });
    setModalOpen(true);
  };

  const useMyLocation = () => {
    if (!navigator.geolocation) {
      showError("Location is not available in this browser.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setForm((current) => ({
          ...current,
          latitude: String(position.coords.latitude),
          longitude: String(position.coords.longitude),
        }));
      },
      () => showError("Could not get your current location.")
    );
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    try {
      const payload: AddressInput = {
        label: form.label,
        recipient_name: form.recipient_name,
        phone: form.phone,
        address_line1: form.address_line1,
        address_line2: form.address_line2 || null,
        city: form.city,
        state: form.state || null,
        postal_code: form.postal_code || null,
        country: form.country,
        latitude: Number(form.latitude),
        longitude: Number(form.longitude),
        delivery_instructions: form.delivery_instructions || null,
      };
      if (editing) {
        await addressService.update(editing.id, payload);
        showSuccess("Address updated.");
      } else {
        await addressService.create(payload);
        showSuccess("Address saved.");
      }
      setModalOpen(false);
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not save this address."));
    } finally {
      setSaving(false);
    }
  };

  const makeDefault = async (address: CustomerAddress) => {
    try {
      await addressService.update(address.id, { is_default: true });
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not set this as your default address."));
    }
  };

  const remove = async (address: CustomerAddress) => {
    if (!window.confirm(`Delete the "${address.label}" address?`)) return;
    try {
      await addressService.remove(address.id);
      showSuccess("Address deleted.");
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not delete this address."));
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="font-display text-2xl font-semibold text-ink">Addresses</h1>
            <p className="text-ink-soft mt-1">Save delivery addresses so checkout is faster later.</p>
          </div>
          <Button onClick={openCreate}>
            <Plus className="h-4 w-4" />
            Add address
          </Button>
        </div>

        {loading ? (
          <SkeletonList />
        ) : addresses.length === 0 ? (
          <EmptyState
            icon={<MapPin className="h-5 w-5" />}
            title="No addresses saved"
            description="Add a delivery address so we can find vendors that serve you."
          />
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {addresses.map((address) => (
              <Card key={address.id}>
                <CardBody className="space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <p className="font-medium text-ink">{address.label}</p>
                    {address.is_default && <Badge tone="primary" icon={<Star className="h-3 w-3" />}>Default</Badge>}
                  </div>
                  <div className="text-sm text-ink-soft space-y-0.5">
                    <p>{address.recipient_name} - {address.phone}</p>
                    <p>{address.address_line1}{address.address_line2 ? `, ${address.address_line2}` : ""}</p>
                    <p>{[address.city, address.state, address.postal_code].filter(Boolean).join(", ")}</p>
                    <p>{address.country}</p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2 pt-1">
                    <Button variant="secondary" size="sm" onClick={() => openEdit(address)}>
                      <Pencil className="h-3.5 w-3.5" />
                      Edit
                    </Button>
                    {!address.is_default && (
                      <Button variant="ghost" size="sm" onClick={() => makeDefault(address)}>
                        <Star className="h-3.5 w-3.5" />
                        Make default
                      </Button>
                    )}
                    <button
                      onClick={() => remove(address)}
                      aria-label="Delete address"
                      className="text-ink-soft hover:text-danger p-1.5 rounded-md hover:bg-danger-soft"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </CardBody>
              </Card>
            ))}
          </div>
        )}
      </div>

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editing ? "Edit address" : "Add address"}
        size="lg"
      >
        <form onSubmit={submit} className="space-y-4">
          <div className="grid sm:grid-cols-2 gap-4">
            <Input
              label="Label"
              value={form.label}
              onChange={(e) => setForm({ ...form, label: e.target.value })}
              placeholder="Home, Work..."
              required
            />
            <Input
              label="Recipient name"
              value={form.recipient_name}
              onChange={(e) => setForm({ ...form, recipient_name: e.target.value })}
              required
            />
          </div>
          <Input
            label="Phone"
            value={form.phone}
            onChange={(e) => setForm({ ...form, phone: e.target.value })}
            placeholder="+1 202 555 0123"
            required
          />
          <Input
            label="Address line 1"
            value={form.address_line1}
            onChange={(e) => setForm({ ...form, address_line1: e.target.value })}
            required
          />
          <Input
            label="Address line 2"
            value={form.address_line2}
            onChange={(e) => setForm({ ...form, address_line2: e.target.value })}
          />
          <div className="grid sm:grid-cols-3 gap-4">
            <Input label="City" value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} required />
            <Input label="State" value={form.state} onChange={(e) => setForm({ ...form, state: e.target.value })} />
            <Input
              label="Postal code"
              value={form.postal_code}
              onChange={(e) => setForm({ ...form, postal_code: e.target.value })}
            />
          </div>
          <Input label="Country" value={form.country} onChange={(e) => setForm({ ...form, country: e.target.value })} required />

          <div className="rounded-md border border-line p-3 space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium text-ink">Coordinates</p>
              <Button type="button" variant="ghost" size="sm" onClick={useMyLocation}>
                <MapPin className="h-3.5 w-3.5" />
                Use my location
              </Button>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Input
                label="Latitude"
                type="number"
                step="any"
                value={form.latitude}
                onChange={(e) => setForm({ ...form, latitude: e.target.value })}
                required
              />
              <Input
                label="Longitude"
                type="number"
                step="any"
                value={form.longitude}
                onChange={(e) => setForm({ ...form, longitude: e.target.value })}
                required
              />
            </div>
          </div>

          <Textarea
            label="Delivery instructions"
            value={form.delivery_instructions}
            onChange={(e) => setForm({ ...form, delivery_instructions: e.target.value })}
            placeholder="Gate code, floor, landmarks..."
          />

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="secondary" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={saving}>
              {editing ? "Save changes" : "Save address"}
            </Button>
          </div>
        </form>
      </Modal>
    </DashboardLayout>
  );
}
