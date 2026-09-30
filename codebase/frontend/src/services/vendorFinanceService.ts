import { apiClient } from "./apiClient";
import type { ApiSuccess } from "../types/auth";
import type { VendorFinancialSummary, VendorPayout, Pagination } from "../types/payments";

export const vendorFinanceService = {
  async getFinancialSummary() {
    const { data } = await apiClient.get<ApiSuccess<VendorFinancialSummary>>("/vendor/financial-summary");
    return data.data;
  },
  async listPayouts(page = 1) {
    const { data } = await apiClient.get<ApiSuccess<{ payouts: VendorPayout[]; pagination: Pagination }>>(
      "/vendor/payouts",
      { params: { page } }
    );
    return data.data;
  },
  async requestPayout(destinationReference: string, amount?: string, idempotencyKey?: string) {
    const { data } = await apiClient.post<ApiSuccess<{ payout: VendorPayout }>>("/vendor/payouts", {
      destination_reference: destinationReference,
      amount,
      idempotency_key: idempotencyKey,
    });
    return data.data.payout;
  },
  async cancelPayout(payoutId: string) {
    const { data } = await apiClient.post<ApiSuccess<{ payout: VendorPayout }>>(`/vendor/payouts/${payoutId}/cancel`);
    return data.data.payout;
  },
};
