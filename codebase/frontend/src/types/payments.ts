export type PaymentStatus =
  | "INITIATED"
  | "PENDING"
  | "SUCCEEDED"
  | "FAILED"
  | "CANCELLED"
  | "PARTIALLY_REFUNDED"
  | "REFUNDED";

export type RefundStatus = "REQUESTED" | "APPROVED" | "REJECTED" | "PROCESSING" | "SUCCEEDED" | "FAILED";

export type VendorPayoutStatus = "REQUESTED" | "PROCESSING" | "PAID" | "FAILED" | "CANCELLED";

export type CommissionRuleStatus = "ACTIVE" | "INACTIVE";

export interface Payment {
  id: string;
  order_id: string;
  order_number: string | null;
  amount: string;
  currency: string;
  method: string;
  provider: string;
  status: PaymentStatus;
  provider_reference: string | null;
  failure_reason: string | null;
  succeeded_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Refund {
  id: string;
  order_id: string;
  payment_id: string;
  amount: string;
  currency: string;
  reason: string;
  status: RefundStatus;
  requested_by: string | null;
  approved_by: string | null;
  provider_reference: string | null;
  failure_reason: string | null;
  approved_at: string | null;
  processed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface RiderWallet {
  id: string;
  rider_id: string;
  currency: string;
  available_balance: string;
  pending_balance: string;
  status: "ACTIVE" | "SUSPENDED";
  created_at: string;
  updated_at: string;
}

export interface WalletTransaction {
  id: string;
  type: "EARNING" | "ADJUSTMENT_CREDIT" | "ADJUSTMENT_DEBIT" | "PAYOUT_DEBIT";
  amount: string;
  currency: string;
  status: "POSTED";
  description: string | null;
  created_at: string;
}

export interface VendorFinancialAccount {
  id: string;
  vendor_id: string;
  currency: string;
  payable_balance: string;
  status: "ACTIVE" | "SUSPENDED";
  created_at: string;
  updated_at: string;
}

export interface VendorFinancialSummary {
  account: VendorFinancialAccount;
  available_for_payout: string;
  lifetime_paid_out: string;
}

export interface VendorPayout {
  id: string;
  vendor_id: string;
  amount: string;
  currency: string;
  status: VendorPayoutStatus;
  destination_reference: string;
  provider_reference: string | null;
  failure_reason: string | null;
  requested_at: string | null;
  processed_at: string | null;
  created_at: string;
}

export interface CommissionRule {
  id: string;
  name: string;
  percentage_rate: string;
  fixed_amount: string;
  scope_type: "GLOBAL" | "VENDOR" | "CATEGORY";
  scope_id: number | null;
  status: CommissionRuleStatus;
  effective_from: string | null;
  effective_to: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReconciliationAccountSummary {
  account_id: string;
  account_type: string;
  owner_type: string;
  owner_id: number | null;
  reconciled_balance: string;
}

export interface ReconciliationSummary {
  accounts: ReconciliationAccountSummary[];
  total_debits: string;
  total_credits: string;
  balanced: boolean;
}

export interface Pagination {
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
}
