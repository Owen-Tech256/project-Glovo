import { useEffect, useState, type FormEvent } from "react";
import { Tag, Plus, Pencil, Pause, Play } from "lucide-react";
import { DashboardLayout } from "../../../layouts/DashboardLayout";
import { Card, CardBody } from "../../../components/ui/Card";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { Select } from "../../../components/ui/Select";
import { Modal } from "../../../components/ui/Modal";
import { Badge } from "../../../components/ui/Badge";
import { EmptyState } from "../../../components/ui/EmptyState";
import { useToast } from "../../../context/ToastContext";
import { promotionService } from "../../../services/promotionService";
import { extractApiErrorMessage } from "../../../services/apiClient";
import type { Promotion } from "../../../types/growth";
import { SkeletonList } from "../../../components/ui/Skeleton";

const emptyForm = {
  name: "",
  code: "",
  type: "PERCENTAGE" as "PERCENTAGE" | "FIXED_AMOUNT" | "FREE_DELIVERY",
  value: "10",
  min_subtotal: "",
  usage_limit_per_customer: "1",
  usage_limit_total: "",
};

export function PromotionsPage() {
  const { showSuccess, showError } = useToast();
  const [promotions, setPromotions] = useState<Promotion[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Promotion | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);

  const load = () => {
    setLoading(true);
    promotionService
      .listVendorPromotions()
      .then(setPromotions)
      .catch(() => showError("Could not load your promotions."))
      .finally(() => setLoading(false));
  };

  useEffect(load, [showError]);

  const openCreate = () => {
    setEditing(null);
    setForm(emptyForm);
    setModalOpen(true);
  };

  const openEdit = (promotion: Promotion) => {
    setEditing(promotion);
    setForm({
      name: promotion.name,
      code: promotion.code ?? "",
      type: promotion.type,
      value: promotion.value,
      min_subtotal: promotion.min_subtotal ?? "",
      usage_limit_per_customer: promotion.usage_limit_per_customer != null ? String(promotion.usage_limit_per_customer) : "",
      usage_limit_total: promotion.usage_limit_total != null ? String(promotion.usage_limit_total) : "",
    });
    setModalOpen(true);
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    try {
      const payload = {
        name: form.name,
        code: form.code || undefined,
        type: form.type,
        value: form.value,
        min_subtotal: form.min_subtotal || undefined,
        usage_limit_per_customer: form.usage_limit_per_customer ? Number(form.usage_limit_per_customer) : undefined,
        usage_limit_total: form.usage_limit_total ? Number(form.usage_limit_total) : undefined,
      };
      if (editing) {
        await promotionService.updateVendorPromotion(editing.id, payload);
        showSuccess("Promotion updated.");
      } else {
        await promotionService.createVendorPromotion(payload);
        showSuccess("Promotion created.");
      }
      setModalOpen(false);
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not save this promotion."));
    } finally {
      setSaving(false);
    }
  };

  const toggleStatus = async (promotion: Promotion) => {
    try {
      await promotionService.updateVendorPromotion(promotion.id, {
        status: promotion.status === "ACTIVE" ? "PAUSED" : "ACTIVE",
      });
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not update this promotion."));
    }
  };

  const valueLabel = (promotion: Promotion) =>
    promotion.type === "PERCENTAGE" ? `${promotion.value}% off` : promotion.type === "FIXED_AMOUNT" ? `$${promotion.value} off` : "Free delivery";

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="font-display text-2xl font-semibold text-ink">Promotions</h1>
            <p className="text-ink-soft mt-1">Discount codes customers can apply at checkout on your orders.</p>
          </div>
          <Button onClick={openCreate}>
            <Plus className="h-4 w-4" />
            New promotion
          </Button>
        </div>

        {loading ? (
          <SkeletonList />
        ) : promotions.length === 0 ? (
          <EmptyState icon={<Tag className="h-5 w-5" />} title="No promotions yet" description="Create a code to help drive orders, e.g. SAVE10." />
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {promotions.map((promotion) => (
              <Card key={promotion.id}>
                <CardBody className="space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="font-medium text-ink">{promotion.name}</p>
                      {promotion.code && <p className="text-xs text-ink-soft font-mono mt-0.5">{promotion.code}</p>}
                    </div>
                    <Badge tone={promotion.status === "ACTIVE" ? "success" : "neutral"}>{promotion.status}</Badge>
                  </div>
                  <p className="text-sm text-ink-soft">{valueLabel(promotion)}</p>
                  <p className="text-xs text-ink-soft">
                    Used {promotion.usage_count}
                    {promotion.usage_limit_total ? ` / ${promotion.usage_limit_total}` : ""} times
                  </p>
                  <div className="flex items-center gap-2 pt-1">
                    <Button variant="secondary" size="sm" onClick={() => openEdit(promotion)}>
                      <Pencil className="h-3.5 w-3.5" />
                      Edit
                    </Button>
                    {(promotion.status === "ACTIVE" || promotion.status === "PAUSED") && (
                      <Button variant="ghost" size="sm" onClick={() => toggleStatus(promotion)}>
                        {promotion.status === "ACTIVE" ? (
                          <>
                            <Pause className="h-3.5 w-3.5" /> Pause
                          </>
                        ) : (
                          <>
                            <Play className="h-3.5 w-3.5" /> Resume
                          </>
                        )}
                      </Button>
                    )}
                  </div>
                </CardBody>
              </Card>
            ))}
          </div>
        )}
      </div>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title={editing ? "Edit promotion" : "New promotion"}>
        <form onSubmit={submit} className="space-y-4">
          <Input label="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          <Input
            label="Code (optional)"
            value={form.code}
            onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })}
            placeholder="SAVE10"
            disabled={Boolean(editing)}
            hint={editing ? "The code can't be changed after creation." : undefined}
          />
          {!editing && (
            <Select label="Discount type" value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value as typeof form.type })}>
              <option value="PERCENTAGE">Percentage off</option>
              <option value="FIXED_AMOUNT">Fixed amount off</option>
              <option value="FREE_DELIVERY">Free delivery</option>
            </Select>
          )}
          {form.type !== "FREE_DELIVERY" && (
            <Input
              label={form.type === "PERCENTAGE" ? "Percentage" : "Amount"}
              type="number"
              step="0.01"
              value={form.value}
              onChange={(e) => setForm({ ...form, value: e.target.value })}
              required
            />
          )}
          <Input
            label="Minimum order subtotal (optional)"
            type="number"
            step="0.01"
            value={form.min_subtotal}
            onChange={(e) => setForm({ ...form, min_subtotal: e.target.value })}
          />
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Uses per customer"
              type="number"
              value={form.usage_limit_per_customer}
              onChange={(e) => setForm({ ...form, usage_limit_per_customer: e.target.value })}
            />
            <Input
              label="Total uses (optional)"
              type="number"
              value={form.usage_limit_total}
              onChange={(e) => setForm({ ...form, usage_limit_total: e.target.value })}
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="secondary" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={saving}>
              {editing ? "Save changes" : "Create promotion"}
            </Button>
          </div>
        </form>
      </Modal>
    </DashboardLayout>
  );
}
