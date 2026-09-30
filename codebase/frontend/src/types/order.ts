import type { CartIssue } from "./cart";
import type { CustomerAddress } from "./catalog";

export type OrderStatus =
  | "CREATED"
  | "PENDING_PAYMENT"
  | "PAYMENT_CONFIRMED"
  | "VENDOR_ACCEPTED"
  | "PREPARING"
  | "READY"
  | "RIDER_ASSIGNED"
  | "PICKED_UP"
  | "DELIVERING"
  | "DELIVERED"
  | "CANCELLED";

export interface OrderItem {
  id: string;
  product_name: string;
  sku: string | null;
  unit_price: string;
  quantity: number;
  line_total: string;
}

export interface OrderAddressSnapshot {
  recipient_name: string;
  phone: string;
  address_line1: string;
  address_line2: string | null;
  city: string;
  state: string | null;
  postal_code: string | null;
  country: string;
  latitude: number | null;
  longitude: number | null;
  delivery_instructions: string | null;
}

export interface AppliedPromotion {
  code: string | null;
  name: string;
  type: "PERCENTAGE" | "FIXED_AMOUNT" | "FREE_DELIVERY";
  value: string;
  discount_amount: string;
  currency: string;
}

export interface Order {
  id: string;
  order_number: string;
  customer_id: string | null;
  branch_id: string;
  branch_name: string | null;
  vendor_name: string | null;
  status: OrderStatus;
  subtotal: string;
  fees: string;
  discount_total: string;
  total: string;
  applied_promotion?: AppliedPromotion | null;
  cancelled_at: string | null;
  cancellation_reason: string | null;
  created_at: string;
  updated_at: string;
  items?: OrderItem[];
  delivery_address?: OrderAddressSnapshot;
}

export interface OrderStatusHistoryEntry {
  from_status: OrderStatus | null;
  to_status: OrderStatus;
  changed_by: string | null;
  changed_by_role: string | null;
  reason: string | null;
  created_at: string;
}

export interface CheckoutResult {
  is_valid: boolean;
  issues: CartIssue[];
  subtotal: string;
  fees: string;
  discount_total: string;
  total: string;
}

export interface CheckoutSummary extends CheckoutResult {
  branch: { id: string; name: string };
  address: CustomerAddress;
  cart: { items: unknown[]; subtotal: string } | null;
  applied_promotion?: AppliedPromotion | null;
  promotion_issue?: string | null;
}

export interface Pagination {
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
}

// The order statuses that make up the vendor prep pipeline, in order -
// used to drive the "advance to next status" action in the vendor queue.
export const VENDOR_NEXT_STATUS: Partial<Record<OrderStatus, OrderStatus>> = {
  PAYMENT_CONFIRMED: "VENDOR_ACCEPTED",
  VENDOR_ACCEPTED: "PREPARING",
  PREPARING: "READY",
};

export const CANCELLABLE_STATUSES: OrderStatus[] = ["CREATED", "PENDING_PAYMENT", "PAYMENT_CONFIRMED", "VENDOR_ACCEPTED"];
