export type CartStatus = "ACTIVE" | "CONVERTED" | "ABANDONED";

export interface CartIssue {
  cart_item_id: string | null;
  product_name: string | null;
  reason: "BRANCH_UNAVAILABLE" | "PRODUCT_UNAVAILABLE" | "CART_EMPTY" | "ADDRESS_OUT_OF_RANGE";
}

export interface CartItem {
  id: string;
  product: {
    id: string;
    name: string;
    description: string | null;
    price: string;
    images?: { id: string; image_url: string; alt_text: string | null }[];
  } | null;
  branch_product_id: string | null;
  quantity: number;
  unit_price_snapshot: string;
  current_unit_price: string | null;
  price_changed: boolean;
  line_total: string | null;
  is_available: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface Cart {
  id: string | null;
  branch_id: string;
  branch_name: string | null;
  status: CartStatus;
  items: CartItem[];
  subtotal: string;
  item_count: number;
  has_issues: boolean;
  issues: CartIssue[];
  discount_total?: string;
  total?: string;
  applied_promotion?: import("./order").AppliedPromotion | null;
  promotion_issue?: string | null;
  created_at: string | null;
  updated_at: string | null;
}
