import { useEffect, useState, type FormEvent } from "react";
import { Megaphone, Plus, Pause, Play, Ban } from "lucide-react";
import { DashboardLayout } from "../../../layouts/DashboardLayout";
import { Card, CardBody } from "../../../components/ui/Card";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { Select } from "../../../components/ui/Select";
import { Modal } from "../../../components/ui/Modal";
import { Badge } from "../../../components/ui/Badge";
import { EmptyState } from "../../../components/ui/EmptyState";
import { useToast } from "../../../context/ToastContext";
import { advertisingService } from "../../../services/advertisingService";
import { extractApiErrorMessage } from "../../../services/apiClient";
import type { AdCampaign, AdCampaignStatus } from "../../../types/growth";
import { SkeletonList } from "../../../components/ui/Skeleton";

const STATUS_TONE: Record<AdCampaignStatus, "success" | "neutral" | "warning" | "danger"> = {
  DRAFT: "neutral",
  PENDING_REVIEW: "warning",
  ACTIVE: "success",
  PAUSED: "neutral",
  BUDGET_EXHAUSTED: "warning",
  REJECTED: "danger",
  COMPLETED: "neutral",
  CANCELLED: "danger",
};

const emptyForm = { name: "", pricing_model: "CPC" as "CPC" | "CPM", bid_amount: "0.50", total_budget: "20.00" };

export function CampaignsPage() {
  const { showSuccess, showError } = useToast();
  const [campaigns, setCampaigns] = useState<AdCampaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);

  const load = () => {
    setLoading(true);
    advertisingService
      .listVendorCampaigns()
      .then(setCampaigns)
      .catch(() => showError("Could not load your ad campaigns."))
      .finally(() => setLoading(false));
  };

  useEffect(load, [showError]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    try {
      await advertisingService.createCampaign({
        name: form.name,
        target_type: "VENDOR",
        pricing_model: form.pricing_model,
        bid_amount: form.bid_amount,
        total_budget: form.total_budget,
      });
      showSuccess("Campaign created and sent for review.");
      setModalOpen(false);
      setForm(emptyForm);
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not create this campaign."));
    } finally {
      setSaving(false);
    }
  };

  const act = async (action: (id: string) => Promise<AdCampaign>, campaignId: string) => {
    try {
      await action(campaignId);
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not update this campaign."));
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="font-display text-2xl font-semibold text-ink">Ad campaigns</h1>
            <p className="text-ink-soft mt-1">Sponsor your storefront to appear more prominently to customers.</p>
          </div>
          <Button onClick={() => setModalOpen(true)}>
            <Plus className="h-4 w-4" />
            New campaign
          </Button>
        </div>

        {loading ? (
          <SkeletonList />
        ) : campaigns.length === 0 ? (
          <EmptyState icon={<Megaphone className="h-5 w-5" />} title="No campaigns yet" description="Launch a campaign to promote your storefront." />
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {campaigns.map((campaign) => (
              <Card key={campaign.id}>
                <CardBody className="space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <p className="font-medium text-ink">{campaign.name}</p>
                    <Badge tone={STATUS_TONE[campaign.status]}>{campaign.status.replace(/_/g, " ")}</Badge>
                  </div>
                  <p className="text-sm text-ink-soft">
                    {campaign.pricing_model} - ${campaign.bid_amount} per {campaign.pricing_model === "CPC" ? "click" : "1,000 views"}
                  </p>
                  <p className="text-xs text-ink-soft">
                    ${campaign.spent_total} spent of ${campaign.total_budget}
                  </p>
                  {campaign.rejection_reason && <p className="text-xs text-danger">{campaign.rejection_reason}</p>}
                  <div className="flex items-center gap-2 pt-1">
                    {campaign.status === "ACTIVE" && (
                      <Button variant="ghost" size="sm" onClick={() => act(advertisingService.pauseCampaign, campaign.id)}>
                        <Pause className="h-3.5 w-3.5" /> Pause
                      </Button>
                    )}
                    {campaign.status === "PAUSED" && (
                      <Button variant="ghost" size="sm" onClick={() => act(advertisingService.resumeCampaign, campaign.id)}>
                        <Play className="h-3.5 w-3.5" /> Resume
                      </Button>
                    )}
                    {!["CANCELLED", "COMPLETED", "REJECTED"].includes(campaign.status) && (
                      <Button variant="ghost" size="sm" onClick={() => act(advertisingService.cancelCampaign, campaign.id)}>
                        <Ban className="h-3.5 w-3.5" /> Cancel
                      </Button>
                    )}
                  </div>
                </CardBody>
              </Card>
            ))}
          </div>
        )}
      </div>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="New ad campaign" description="Campaigns are reviewed before they go live.">
        <form onSubmit={submit} className="space-y-4">
          <Input label="Campaign name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          <Select
            label="Pricing model"
            value={form.pricing_model}
            onChange={(e) => setForm({ ...form, pricing_model: e.target.value as "CPC" | "CPM" })}
          >
            <option value="CPC">Cost per click</option>
            <option value="CPM">Cost per 1,000 impressions</option>
          </Select>
          <Input
            label="Bid amount"
            type="number"
            step="0.0001"
            value={form.bid_amount}
            onChange={(e) => setForm({ ...form, bid_amount: e.target.value })}
            required
          />
          <Input
            label="Total budget"
            type="number"
            step="0.01"
            value={form.total_budget}
            onChange={(e) => setForm({ ...form, total_budget: e.target.value })}
            hint="Spend is capped at your available payout balance."
            required
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="secondary" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={saving}>
              Create campaign
            </Button>
          </div>
        </form>
      </Modal>
    </DashboardLayout>
  );
}
