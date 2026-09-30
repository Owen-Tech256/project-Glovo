import { apiClient } from "./apiClient";
import type { ApiSuccess } from "../types/auth";
import type {
  Payment,
  Refund,
  VendorPayout,
  CommissionRule,
  ReconciliationSummary,
  Pagination,
} from "../types/payments";

export const adminFinanceService = {
  // --- Payments ---
  async listPayments(params: { status?: string; page?: number }) {
    const { data } = await apiClient.get<ApiSuccess<{ payments: Payment[]; pagination: Pagination }>>(
      "/admin/payments",
      { params: { status: params.status || undefined, page: params.page ?? 1 } }
    );
    return data.data;
  },

  // --- Refunds ---
  async listRefunds(params: { status?: string; page?: number }) {
    const { data } = await apiClient.get<ApiSuccess<{ refunds: Refund[]; pagination: Pagination }>>(
      "/admin/refunds",
      { params: { status: params.status || undefined, page: params.page ?? 1 } }
    );
    return data.data;
  },
  async approveRefund(refundId: string) {
    const { data } = await apiClient.post<ApiSuccess<{ refund: Refund }>>(`/admin/refunds/${refundId}/approve`);
    return data.data.refund;
  },
  async rejectRefund(refundId: string, reason?: string) {
    const { data } = await apiClient.post<ApiSuccess<{ refund: Refund }>>(`/admin/refunds/${refundId}/reject`, {
      reason,
    });
    return data.data.refund;
  },
  async retryRefund(refundId: string) {
    const { data } = await apiClient.post<ApiSuccess<{ refund: Refund }>>(`/admin/refunds/${refundId}/retry`);
    return data.data.refund;
  },

  // --- Payouts ---
  async listPayouts(params: { status?: string; page?: number }) {
    const { data } = await apiClient.get<ApiSuccess<{ payouts: VendorPayout[]; pagination: Pagination }>>(
      "/admin/payouts",
      { params: { status: params.status || undefined, page: params.page ?? 1 } }
    );
    return data.data;
  },
  async retryPayout(payoutId: string) {
    const { data } = await apiClient.post<ApiSuccess<{ payout: VendorPayout }>>(`/admin/payouts/${payoutId}/retry`);
    return data.data.payout;
  },

  // --- Commission rules ---
  async listCommissionRules(status?: string) {
    const { data } = await apiClient.get<ApiSuccess<{ commission_rules: CommissionRule[] }>>(
      "/admin/commission-rules",
      { params: { status: status || undefined } }
    );
    return data.data.commission_rules;
  },
  async createCommissionRule(payload: { name: string; percentage_rate: string; fixed_amount?: string }) {
    const { data } = await apiClient.post<ApiSuccess<{ commission_rule: CommissionRule }>>(
      "/admin/commission-rules",
      payload
    );
    return data.data.commission_rule;
  },
  async updateCommissionRule(ruleId: string, payload: Partial<{ percentage_rate: string; fixed_amount: string; status: string }>) {
    const { data } = await apiClient.patch<ApiSuccess<{ commission_rule: CommissionRule }>>(
      `/admin/commission-rules/${ruleId}`,
      payload
    );
    return data.data.commission_rule;
  },

  // --- Wallet adjustments ---
  async createWalletAdjustment(riderId: string, amount: string, reason: string) {
    const { data } = await apiClient.post<ApiSuccess<{ wallet_transaction: unknown }>>("/admin/wallet-adjustments", {
      rider_id: riderId,
      amount,
      reason,
    });
    return data.data;
  },

  // --- Reconciliation ---
  async getReconciliationSummary() {
    const { data } = await apiClient.get<ApiSuccess<ReconciliationSummary>>("/admin/reconciliation/summary");
    return data.data;
  },
};
