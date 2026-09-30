import { useEffect, useState } from "react";
import { Tag } from "lucide-react";
import { DashboardLayout } from "../../../layouts/DashboardLayout";
import { Card, CardBody } from "../../../components/ui/Card";
import { Badge } from "../../../components/ui/Badge";
import { EmptyState } from "../../../components/ui/EmptyState";
import { useToast } from "../../../context/ToastContext";
import { promotionService } from "../../../services/promotionService";
import type { Promotion } from "../../../types/growth";
import { SkeletonList } from "../../../components/ui/Skeleton";

export function CustomerPromotionsPage() {
  const { showError } = useToast();
  const [promotions, setPromotions] = useState<Promotion[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    promotionService
      .listPublicPromotions()
      .then(setPromotions)
      .catch(() => showError("Could not load current promotions."))
      .finally(() => setLoading(false));
  }, [showError]);

  const valueLabel = (promotion: Promotion) =>
    promotion.type === "PERCENTAGE" ? `${promotion.value}% off` : promotion.type === "FIXED_AMOUNT" ? `$${promotion.value} off` : "Free delivery";

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink">Promotions</h1>
          <p className="text-ink-soft mt-1">Enter a code at checkout to apply it to your order.</p>
        </div>

        {loading ? (
          <SkeletonList />
        ) : promotions.length === 0 ? (
          <EmptyState icon={<Tag className="h-5 w-5" />} title="No active promotions" description="Check back soon for new offers." />
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {promotions.map((promotion) => (
              <Card key={promotion.id}>
                <CardBody className="space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <p className="font-medium text-ink">{promotion.name}</p>
                    {!promotion.vendor_id && <Badge tone="primary">Platform-wide</Badge>}
                  </div>
                  <p className="text-sm text-primary font-medium">{valueLabel(promotion)}</p>
                  {promotion.description && <p className="text-sm text-ink-soft">{promotion.description}</p>}
                  {promotion.code && (
                    <p className="mt-2 inline-block rounded-md bg-paper px-2.5 py-1 font-mono text-xs text-ink">{promotion.code}</p>
                  )}
                  {promotion.min_subtotal && (
                    <p className="text-xs text-ink-soft">Minimum order ${promotion.min_subtotal}</p>
                  )}
                </CardBody>
              </Card>
            ))}
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
