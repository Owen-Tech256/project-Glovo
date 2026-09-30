import { useEffect, useState } from "react";
import { Star, MessageSquare } from "lucide-react";
import { DashboardLayout } from "../../../layouts/DashboardLayout";
import { Card, CardBody } from "../../../components/ui/Card";
import { Button } from "../../../components/ui/Button";
import { Textarea } from "../../../components/ui/Textarea";
import { EmptyState } from "../../../components/ui/EmptyState";
import { useToast } from "../../../context/ToastContext";
import { reviewService } from "../../../services/reviewService";
import { extractApiErrorMessage } from "../../../services/apiClient";
import type { Review } from "../../../types/growth";
import { SkeletonList } from "../../../components/ui/Skeleton";

function Stars({ rating }: { rating: number }) {
  return (
    <div className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map((n) => (
        <Star key={n} className={`h-3.5 w-3.5 ${n <= rating ? "fill-primary text-primary" : "text-line-strong"}`} />
      ))}
    </div>
  );
}

export function VendorReviewsPage({ isRider = false }: { isRider?: boolean }) {
  const { showSuccess, showError } = useToast();
  const [reviews, setReviews] = useState<Review[]>([]);
  const [loading, setLoading] = useState(true);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    const fetcher = isRider ? reviewService.listMyRiderReviews : reviewService.listMyVendorReviews;
    fetcher()
      .then(setReviews)
      .catch(() => showError("Could not load your reviews."))
      .finally(() => setLoading(false));
  };

  useEffect(load, [showError, isRider]);

  async function respond(reviewId: string) {
    const body = drafts[reviewId];
    if (!body?.trim()) return;
    setSubmitting(reviewId);
    try {
      await reviewService.respondToReview(reviewId, body.trim());
      showSuccess("Response posted.");
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not post your response."));
    } finally {
      setSubmitting(null);
    }
  }

  return (
    <DashboardLayout>
      <div className="space-y-6 max-w-2xl">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink">Reviews</h1>
          <p className="text-ink-soft mt-1">What customers are saying, and your responses.</p>
        </div>

        {loading ? (
          <SkeletonList />
        ) : reviews.length === 0 ? (
          <EmptyState icon={<Star className="h-5 w-5" />} title="No reviews yet" description="Reviews from customers will show up here." />
        ) : (
          <div className="space-y-4">
            {reviews.map((review) => (
              <Card key={review.id}>
                <CardBody className="space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <Stars rating={review.rating} />
                      <p className="text-xs text-ink-soft mt-1">
                        {review.customer_name ?? "A customer"} - {new Date(review.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  {review.body && <p className="text-sm text-ink">{review.body}</p>}

                  {review.response ? (
                    <div className="rounded-lg bg-paper px-3 py-2 text-sm">
                      <p className="flex items-center gap-1.5 text-xs font-medium text-ink-soft">
                        <MessageSquare className="h-3 w-3" /> Your response
                      </p>
                      <p className="mt-1 text-ink">{review.response.body}</p>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <Textarea
                        label="Respond"
                        value={drafts[review.id] ?? ""}
                        onChange={(e) => setDrafts((prev) => ({ ...prev, [review.id]: e.target.value }))}
                        placeholder="Thanks for your feedback..."
                      />
                      <Button size="sm" isLoading={submitting === review.id} onClick={() => respond(review.id)}>
                        Post response
                      </Button>
                    </div>
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
