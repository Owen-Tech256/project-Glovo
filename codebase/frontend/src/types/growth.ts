export type PromotionType = "PERCENTAGE" | "FIXED_AMOUNT" | "FREE_DELIVERY";
export type PromotionScopeType = "ORDER" | "VENDOR" | "BRANCH" | "CATEGORY" | "PRODUCT";
export type PromotionStatus = "DRAFT" | "ACTIVE" | "PAUSED" | "EXPIRED" | "ARCHIVED";

export interface Promotion {
  id: string;
  vendor_id: string | null;
  name: string;
  description: string | null;
  code: string | null;
  type: PromotionType;
  value: string;
  max_discount_amount: string | null;
  min_subtotal: string | null;
  scope_type: PromotionScopeType;
  usage_limit_total: number | null;
  usage_limit_per_customer: number | null;
  usage_count: number;
  status: PromotionStatus;
  starts_at: string | null;
  ends_at: string | null;
  is_currently_active: boolean;
  created_at: string;
}

export type AdCampaignStatus =
  | "DRAFT" | "PENDING_REVIEW" | "ACTIVE" | "PAUSED" | "BUDGET_EXHAUSTED" | "REJECTED" | "COMPLETED" | "CANCELLED";
export type AdTargetType = "VENDOR" | "BRANCH" | "PRODUCT" | "CATEGORY";
export type AdPricingModel = "CPC" | "CPM";

export interface AdCampaign {
  id: string;
  vendor_id: string | null;
  name: string;
  objective: "SPONSORED_LISTING" | "BANNER";
  target_type: AdTargetType;
  target_id: number;
  pricing_model: AdPricingModel;
  bid_amount: string;
  daily_budget: string | null;
  total_budget: string;
  spent_total: string;
  remaining_budget: string;
  status: AdCampaignStatus;
  rejection_reason: string | null;
  starts_at: string | null;
  ends_at: string | null;
  created_at: string;
  performance?: { impressions: number; clicks: number; click_through_rate: string; spent_total: string; remaining_budget: string };
}

export type ReviewTargetType = "VENDOR" | "RIDER" | "PRODUCT";
export type ReviewStatus = "PUBLISHED" | "PENDING_REVIEW" | "HIDDEN" | "REMOVED";

export interface ReviewResponse {
  body: string;
  status: "PUBLISHED" | "HIDDEN";
  created_at: string;
}

export interface Review {
  id: string;
  customer_id: string | null;
  customer_name: string | null;
  order_id: string | null;
  target_type: ReviewTargetType;
  rating: number;
  body: string | null;
  status: ReviewStatus;
  edited_at: string | null;
  created_at: string;
  response?: ReviewResponse;
}

export interface ReviewableTarget {
  target_type: ReviewTargetType;
  target_id: string;
  target_name: string;
  existing_review: Review | null;
}

export interface ReviewReport {
  id: string;
  review_id: string | null;
  reporter_id: string | null;
  reason: string;
  status: "PENDING" | "REVIEWED" | "DISMISSED";
  created_at: string;
}

export type NotificationCategory =
  | "ORDER" | "PAYMENT" | "DELIVERY" | "PROMOTION" | "REVIEW" | "PAYOUT" | "ADVERTISING" | "ACCOUNT";

export interface AppNotification {
  id: string;
  category: NotificationCategory;
  title: string;
  body: string;
  entity_type: string | null;
  entity_id: string | null;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
}

export interface NotificationPreference {
  category: NotificationCategory;
  channel: "EMAIL" | "SMS" | "PUSH";
  enabled: boolean;
}

export interface NotificationTemplate {
  id: string;
  key: string;
  channel: "IN_APP" | "EMAIL" | "SMS" | "PUSH";
  category: string;
  title_template: string;
  body_template: string;
  version: number;
  status: "ACTIVE" | "INACTIVE";
}
