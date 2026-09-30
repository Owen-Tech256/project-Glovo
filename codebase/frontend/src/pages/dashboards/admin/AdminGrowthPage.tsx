import { useEffect, useState } from "react";
import { Sparkles, Tag, Megaphone, Star, MessageCircle } from "lucide-react";
import { DashboardLayout } from "../../../layouts/DashboardLayout";
import { Card, CardBody } from "../../../components/ui/Card";
import { Button } from "../../../components/ui/Button";
import { Modal } from "../../../components/ui/Modal";
import { Textarea } from "../../../components/ui/Textarea";
import { Badge, StatusBadge } from "../../../components/ui/Badge";
import { EmptyState } from "../../../components/ui/EmptyState";
import { useToast } from "../../../context/ToastContext";
import { promotionService } from "../../../services/promotionService";
import { advertisingService } from "../../../services/advertisingService";
import { reviewService } from "../../../services/reviewService";
import { extractApiErrorMessage } from "../../../services/apiClient";
import type { Promotion, AdCampaign, Review, ReviewReport } from "../../../types/growth";
import { SkeletonList } from "../../../components/ui/Skeleton";

type Tab = "promotions" | "campaigns" | "reviews" | "reports";

const TABS: { id: Tab; label: string; icon: React.ReactNode }[] = [
  { id: "promotions", label: "Promotions", icon: <Tag className="h-4 w-4" /> },
  { id: "campaigns", label: "Ad campaigns", icon: <Megaphone className="h-4 w-4" /> },
  { id: "reviews", label: "Reviews", icon: <Star className="h-4 w-4" /> },
  { id: "reports", label: "Reports", icon: <MessageCircle className="h-4 w-4" /> },
];

export function AdminGrowthPage() {
  const { showError, showSuccess } = useToast();
  const [tab, setTab] = useState<Tab>("promotions");

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink flex items-center gap-2">
            <Sparkles className="h-6 w-6" /> Growth
          </h1>
          <p className="text-ink-soft mt-1">Promotions, advertising, and review moderation across the platform.</p>
        </div>

        <div className="flex flex-wrap gap-1.5 border-b border-line pb-3">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                tab === t.id ? "bg-primary-soft text-primary-dark" : "text-ink-soft hover:bg-ink/[0.04] hover:text-ink"
              }`}
            >
              {t.icon}
              {t.label}
            </button>
          ))}
        </div>

        {tab === "promotions" && <PromotionsTab showError={showError} />}
        {tab === "campaigns" && <CampaignsTab showError={showError} showSuccess={showSuccess} />}
        {tab === "reviews" && <ReviewsTab showError={showError} showSuccess={showSuccess} />}
        {tab === "reports" && <ReportsTab showError={showError} showSuccess={showSuccess} />}
      </div>
    </DashboardLayout>
  );
}

function PromotionsTab({ showError }: { showError: (msg: string) => void }) {
  const [promotions, setPromotions] = useState<Promotion[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    promotionService
      .listAllPromotions()
      .then(setPromotions)
      .catch(() => showError("Could not load promotions."))
      .finally(() => setLoading(false));
  }, [showError]);

  if (loading) return <SkeletonList />;
  if (promotions.length === 0) return <EmptyState icon={<Tag className="h-5 w-5" />} title="No promotions" description="Nothing here yet." />;

  return (
    <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {promotions.map((promotion) => (
        <Card key={promotion.id}>
          <CardBody className="space-y-2">
            <div className="flex items-start justify-between gap-2">
              <p className="font-medium text-ink">{promotion.name}</p>
              <Badge tone={promotion.status === "ACTIVE" ? "success" : "neutral"}>{promotion.status}</Badge>
            </div>
            <p className="text-xs text-ink-soft">{promotion.vendor_id ? `Vendor promotion` : "Platform-wide"}</p>
            {promotion.code && <p className="text-xs font-mono text-ink-soft">{promotion.code}</p>}
            <p className="text-xs text-ink-soft">Used {promotion.usage_count} times</p>
          </CardBody>
        </Card>
      ))}
    </div>
  );
}

function CampaignsTab({ showError, showSuccess }: { showError: (msg: string) => void; showSuccess: (msg: string) => void }) {
  const [campaigns, setCampaigns] = useState<AdCampaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [rejectTarget, setRejectTarget] = useState<AdCampaign | null>(null);
  const [reason, setReason] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    advertisingService
      .listAllCampaigns()
      .then(setCampaigns)
      .catch(() => showError("Could not load ad campaigns."))
      .finally(() => setLoading(false));
  };

  useEffect(load, [showError]);

  async function approve(campaign: AdCampaign) {
    setBusyId(campaign.id);
    try {
      await advertisingService.approveCampaign(campaign.id);
      showSuccess("Campaign approved.");
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not approve this campaign."));
    } finally {
      setBusyId(null);
    }
  }

  async function reject() {
    if (!rejectTarget) return;
    setBusyId(rejectTarget.id);
    try {
      await advertisingService.rejectCampaign(rejectTarget.id, reason);
      showSuccess("Campaign rejected.");
      setRejectTarget(null);
      setReason("");
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not reject this campaign."));
    } finally {
      setBusyId(null);
    }
  }

  if (loading) return <SkeletonList />;
  if (campaigns.length === 0) return <EmptyState icon={<Megaphone className="h-5 w-5" />} title="No campaigns" description="Nothing here yet." />;

  return (
    <>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {campaigns.map((campaign) => (
          <Card key={campaign.id}>
            <CardBody className="space-y-2">
              <div className="flex items-start justify-between gap-2">
                <p className="font-medium text-ink">{campaign.name}</p>
                <StatusBadge status={campaign.status} />
              </div>
              <p className="text-xs text-ink-soft">
                {campaign.pricing_model} - ${campaign.bid_amount}
              </p>
              <p className="text-xs text-ink-soft">
                ${campaign.spent_total} / ${campaign.total_budget}
              </p>
              {campaign.status === "PENDING_REVIEW" && (
                <div className="flex items-center gap-2 pt-1">
                  <Button size="sm" isLoading={busyId === campaign.id} onClick={() => approve(campaign)}>
                    Approve
                  </Button>
                  <Button size="sm" variant="secondary" onClick={() => setRejectTarget(campaign)}>
                    Reject
                  </Button>
                </div>
              )}
            </CardBody>
          </Card>
        ))}
      </div>

      <Modal open={Boolean(rejectTarget)} onClose={() => setRejectTarget(null)} title="Reject campaign">
        <div className="space-y-4">
          <Textarea label="Reason" value={reason} onChange={(e) => setReason(e.target.value)} required />
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setRejectTarget(null)}>
              Cancel
            </Button>
            <Button variant="danger" isLoading={Boolean(busyId)} disabled={!reason.trim()} onClick={reject}>
              Reject
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
}

function ReviewsTab({ showError, showSuccess }: { showError: (msg: string) => void; showSuccess: (msg: string) => void }) {
  const [reviews, setReviews] = useState<Review[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    reviewService
      .listAllReviews()
      .then(setReviews)
      .catch(() => showError("Could not load reviews."))
      .finally(() => setLoading(false));
  };

  useEffect(load, [showError]);

  async function moderate(review: Review, status: string) {
    setBusyId(review.id);
    try {
      await reviewService.moderateReview(review.id, status);
      showSuccess("Review updated.");
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not update this review."));
    } finally {
      setBusyId(null);
    }
  }

  if (loading) return <SkeletonList />;
  if (reviews.length === 0) return <EmptyState icon={<Star className="h-5 w-5" />} title="No reviews" description="Nothing here yet." />;

  return (
    <div className="space-y-3">
      {reviews.map((review) => (
        <Card key={review.id}>
          <CardBody className="flex items-start justify-between gap-3">
            <div>
              <p className="text-sm text-ink">
                {review.rating}/5 by {review.customer_name ?? "a customer"}
              </p>
              {review.body && <p className="text-sm text-ink-soft mt-1">{review.body}</p>}
              <Badge tone={review.status === "PUBLISHED" ? "success" : "neutral"}>{review.status}</Badge>
            </div>
            <div className="flex shrink-0 gap-2">
              {review.status !== "HIDDEN" && (
                <Button size="sm" variant="secondary" isLoading={busyId === review.id} onClick={() => moderate(review, "HIDDEN")}>
                  Hide
                </Button>
              )}
              {review.status !== "PUBLISHED" && (
                <Button size="sm" isLoading={busyId === review.id} onClick={() => moderate(review, "PUBLISHED")}>
                  Publish
                </Button>
              )}
            </div>
          </CardBody>
        </Card>
      ))}
    </div>
  );
}

function ReportsTab({ showError, showSuccess }: { showError: (msg: string) => void; showSuccess: (msg: string) => void }) {
  const [reports, setReports] = useState<ReviewReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    reviewService
      .listReviewReports("PENDING")
      .then(setReports)
      .catch(() => showError("Could not load review reports."))
      .finally(() => setLoading(false));
  };

  useEffect(load, [showError]);

  async function resolve(report: ReviewReport, status: "REVIEWED" | "DISMISSED", hideReview: boolean) {
    setBusyId(report.id);
    try {
      await reviewService.resolveReviewReport(report.id, status, hideReview);
      showSuccess("Report resolved.");
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not resolve this report."));
    } finally {
      setBusyId(null);
    }
  }

  if (loading) return <SkeletonList />;
  if (reports.length === 0)
    return <EmptyState icon={<MessageCircle className="h-5 w-5" />} title="No pending reports" description="Reported reviews will show up here." />;

  return (
    <div className="space-y-3">
      {reports.map((report) => (
        <Card key={report.id}>
          <CardBody className="flex items-start justify-between gap-3">
            <p className="text-sm text-ink">{report.reason}</p>
            <div className="flex shrink-0 gap-2">
              <Button size="sm" variant="danger" isLoading={busyId === report.id} onClick={() => resolve(report, "REVIEWED", true)}>
                Hide review
              </Button>
              <Button size="sm" variant="secondary" isLoading={busyId === report.id} onClick={() => resolve(report, "DISMISSED", false)}>
                Dismiss
              </Button>
            </div>
          </CardBody>
        </Card>
      ))}
    </div>
  );
}
