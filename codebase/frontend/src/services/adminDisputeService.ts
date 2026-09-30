import { apiClient } from "./apiClient";
import type { ApiSuccess } from "../types/auth";
import type { Dispute, DisputeEvidence, DisputeAction } from "../types/disputes";
import type { Pagination } from "../types/support";

export interface DisputeFilters {
  status?: string;
  category?: string;
  priority?: string;
  page?: number;
}

export const adminDisputeService = {
  async listDisputes(filters: DisputeFilters) {
    const { data } = await apiClient.get<ApiSuccess<{ disputes: Dispute[]; pagination: Pagination }>>(
      "/admin/disputes",
      { params: filters }
    );
    return data.data;
  },

  async getDispute(disputeId: string) {
    const { data } = await apiClient.get<ApiSuccess<{ dispute: Dispute }>>(`/admin/disputes/${disputeId}`);
    return data.data.dispute;
  },

  async addEvidence(disputeId: string, evidenceType: string, secureReference?: string, description?: string) {
    const { data } = await apiClient.post<ApiSuccess<{ evidence: DisputeEvidence }>>(
      `/admin/disputes/${disputeId}/evidence`,
      { evidence_type: evidenceType, secure_reference: secureReference, description }
    );
    return data.data.evidence;
  },

  async updatePriority(disputeId: string, priority: string) {
    const { data } = await apiClient.patch<ApiSuccess<{ dispute: Dispute }>>(`/admin/disputes/${disputeId}/priority`, {
      priority,
    });
    return data.data.dispute;
  },

  async recordAction(disputeId: string, actionType: string, reason?: string) {
    const { data } = await apiClient.post<ApiSuccess<{ action: DisputeAction }>>(
      `/admin/disputes/${disputeId}/actions`,
      { action_type: actionType, reason }
    );
    return data.data.action;
  },

  async resolve(disputeId: string, status: string, resolution?: string) {
    const { data } = await apiClient.post<ApiSuccess<{ dispute: Dispute }>>(`/admin/disputes/${disputeId}/resolve`, {
      status,
      resolution,
    });
    return data.data.dispute;
  },

  async resolveWithRefund(disputeId: string, reason: string, amount?: string) {
    const { data } = await apiClient.post<ApiSuccess<{ dispute: Dispute; action: DisputeAction }>>(
      `/admin/disputes/${disputeId}/resolve-with-refund`,
      { reason, amount: amount || undefined }
    );
    return data.data;
  },
};
