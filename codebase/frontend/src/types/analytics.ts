export interface OrdersMetrics {
  date_from: string;
  date_to: string;
  total_orders: number;
  orders_by_status: Record<string, number>;
  delivered_orders: number;
  cancelled_orders: number;
  completion_rate: number;
  cancellation_rate: number;
  gross_order_value: string;
  average_order_value: string;
}

export interface FinanceMetrics {
  date_from: string;
  date_to: string;
  total_payment_attempts: number;
  successful_payments: number;
  payment_success_rate: number;
  gross_revenue: string;
  platform_commission_revenue: string;
  platform_ad_revenue: string;
  total_refunded: string;
  vendor_payouts_paid: string;
  rider_earnings_accrued: string;
  net_platform_revenue: string;
}

export interface VendorMetricRow {
  vendor_id: string;
  vendor_name: string;
  order_count: number;
  gross_sales: string;
  discounts: string;
  refunds: string;
  net_sales: string;
  average_order_value: string;
}

export interface RiderMetricRow {
  rider_id: string;
  rating_average: string | null;
  completed_deliveries: number;
  offers_received: number;
  acceptance_rate: number;
  rejection_rate: number;
  earnings: string;
}

export interface DeliveryMetrics {
  date_from: string;
  date_to: string;
  total_deliveries: number;
  completed_deliveries: number;
  cancelled_deliveries: number;
  failure_rate: number;
  avg_assignment_seconds: number | null;
  avg_pickup_seconds: number | null;
  avg_total_duration_seconds: number | null;
}

export interface CustomerMetrics {
  date_from: string;
  date_to: string;
  new_registrations: number;
  active_customers: number;
  repeat_customers: number;
  repeat_rate: number;
  average_orders_per_active_customer: number;
}

export interface PromotionAdMetrics {
  date_from: string;
  date_to: string;
  active_promotions: number;
  promotion_redemptions: number;
  promotion_discount_total: string;
  active_ad_campaigns: number;
  ad_impressions: number;
  ad_clicks: number;
  ad_ctr: number;
  ad_spend: string;
}

export interface SupportDisputeMetrics {
  date_from: string;
  date_to: string;
  tickets: {
    total: number;
    by_status: Record<string, number>;
    by_category: Record<string, number>;
    backlog: number;
    avg_resolution_seconds: number | null;
  };
  disputes: {
    total: number;
    by_status: Record<string, number>;
    by_category: Record<string, number>;
    backlog: number;
    avg_resolution_seconds: number | null;
  };
}

export interface AnalyticsOverview {
  orders: OrdersMetrics;
  finance: FinanceMetrics;
  delivery: DeliveryMetrics;
  customers: CustomerMetrics;
  support_disputes: SupportDisputeMetrics;
}
