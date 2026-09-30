import { apiClient } from "./apiClient";
import type { ApiSuccess } from "../types/auth";
import type { Dispute, DisputeEvidence } from "../types/disputes";
import type { Pagination } from "../types/support";

export const disputeService = {
  async createDispute(payload: {
    order_id: string;
    category: string;
    description: string;
    delivery_id?: string;
    payment_id?: string;
    refund_id?: string;
    ticket_id?: string;
  }) {
    const { data } = await apiClient.post<ApiSuccess<{ dispute: Dispute }>>("/disputes", payload);
    return data.data.dispute;
  },

  async listMyDisputes(page = 1) {
    const { data } = await apiClient.get<ApiSuccess<{ disputes: Dispute[]; pagination: Pagination }>>("/disputes", {
      params: { page },
    });
    return data.data;
  },

  async getDispute(disputeId: string) {
    const { data } = await apiClient.get<ApiSuccess<{ dispute: Dispute }>>(`/disputes/${disputeId}`);
    return data.data.dispute;
  },

  async addEvidence(disputeId: string, evidenceType: string, secureReference?: string, description?: string) {
    const { data } = await apiClient.post<ApiSuccess<{ evidence: DisputeEvidence }>>(
      `/disputes/${disputeId}/evidence`,
      { evidence_type: evidenceType, secure_reference: secureReference, description }
    );
    return data.data.evidence;
  },
};
