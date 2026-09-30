import { useEffect, useState, type FormEvent } from "react";
import { Store, Save } from "lucide-react";
import { DashboardLayout } from "../../../layouts/DashboardLayout";
import { Card, CardHeader, CardBody } from "../../../components/ui/Card";
import { Input } from "../../../components/ui/Input";
import { Textarea } from "../../../components/ui/Textarea";
import { Button } from "../../../components/ui/Button";
import { StatusBadge } from "../../../components/ui/Badge";
import { useToast } from "../../../context/ToastContext";
import { vendorService } from "../../../services/vendorService";
import { extractApiErrorMessage } from "../../../services/apiClient";
import type { Vendor } from "../../../types/catalog";
import { SkeletonBlock } from "../../../components/ui/Skeleton";

export function BusinessProfilePage() {
  const { showSuccess, showError } = useToast();
  const [vendor, setVendor] = useState<Vendor | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ name: "", description: "", phone: "", email: "", logo_url: "" });

  useEffect(() => {
    let active = true;
    vendorService
      .getMyVendor()
      .then((v) => {
        if (!active) return;
        setVendor(v);
        setForm({
          name: v.name ?? "",
          description: v.description ?? "",
          phone: v.phone ?? "",
          email: v.email ?? "",
          logo_url: v.logo_url ?? "",
        });
      })
      .catch(() => showError("Could not load your business profile."))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [showError]);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    try {
      const updated = await vendorService.updateMyVendor({
        name: form.name,
        description: form.description || null,
        phone: form.phone || null,
        email: form.email || null,
        logo_url: form.logo_url || null,
      });
      setVendor(updated);
      showSuccess("Business profile updated.");
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not update your business profile."));
    } finally {
      setSaving(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="font-display text-2xl font-semibold text-ink">Business profile</h1>
            <p className="text-ink-soft mt-1">This is how customers will see your business.</p>
          </div>
          {vendor && <StatusBadge status={vendor.status} />}
        </div>

        <Card className="max-w-2xl">
          <CardHeader className="flex items-center gap-2.5">
            <Store className="h-4.5 w-4.5 text-primary" />
            <span className="font-medium text-ink">Details</span>
          </CardHeader>
          <CardBody>
            {loading ? (
              <SkeletonBlock className="h-64" />
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                <Input
                  label="Business name"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  required
                />
                <Textarea
                  label="Description"
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  placeholder="Tell customers what makes your business great."
                />
                <div className="grid sm:grid-cols-2 gap-4">
                  <Input
                    label="Phone"
                    value={form.phone}
                    onChange={(e) => setForm({ ...form, phone: e.target.value })}
                    placeholder="+1 202 555 0123"
                  />
                  <Input
                    label="Email"
                    type="email"
                    value={form.email}
                    onChange={(e) => setForm({ ...form, email: e.target.value })}
                  />
                </div>
                <Input
                  label="Logo URL"
                  value={form.logo_url}
                  onChange={(e) => setForm({ ...form, logo_url: e.target.value })}
                  placeholder="https://..."
                />
                <div className="pt-2">
                  <Button type="submit" isLoading={saving}>
                    <Save className="h-4 w-4" />
                    Save changes
                  </Button>
                </div>
              </form>
            )}
          </CardBody>
        </Card>
      </div>
    </DashboardLayout>
  );
}
