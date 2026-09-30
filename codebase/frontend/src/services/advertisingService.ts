import { apiClient } from "./apiClient";
import type { ApiSuccess } from "../types/auth";
import type { AdCampaign } from "../types/growth";

export interface AdCampaignInput {
  name: string;
  objective?: "SPONSORED_LISTING" | "BANNER";
  target_type: "VENDOR" | "BRANCH" | "PRODUCT" | "CATEGORY";
  target_id?: string;
  pricing_model?: "CPC" | "CPM";
  bid_amount: string;
  daily_budget?: string;
  total_budget: string;
  starts_at?: string;
  ends_at?: string;
}

export const advertisingService = {
  // --- Tracking (any authenticated role) ---
  async recordEvent(campaignId: string, eventType: "IMPRESSION" | "CLICK", eventReference?: string) {
    await apiClient.post(`/ads/campaigns/${campaignId}/events`, { event_type: eventType, event_reference: eventReference });
  },

  // --- Vendor management ---
  async listVendorCampaigns(status?: string) {
    const { data } = await apiClient.get<ApiSuccess<{ campaigns: AdCampaign[] }>>(
      "/vendor/ad-campaigns", { params: status ? { status } : undefined }
    );
    return data.data.campaigns;
  },
  async getVendorCampaign(campaignId: string) {
    const { data } = await apiClient.get<ApiSuccess<{ campaign: AdCampaign }>>(`/vendor/ad-campaigns/${campaignId}`);
    return data.data.campaign;
  },
  async createCampaign(input: AdCampaignInput) {
    const { data } = await apiClient.post<ApiSuccess<{ campaign: AdCampaign }>>("/vendor/ad-campaigns", input);
    return data.data.campaign;
  },
  async updateCampaign(campaignId: string, input: Partial<AdCampaignInput>) {
    const { data } = await apiClient.patch<ApiSuccess<{ campaign: AdCampaign }>>(`/vendor/ad-campaigns/${campaignId}`, input);
    return data.data.campaign;
  },
  async pauseCampaign(campaignId: string) {
    const { data } = await apiClient.post<ApiSuccess<{ campaign: AdCampaign }>>(`/vendor/ad-campaigns/${campaignId}/pause`);
    return data.data.campaign;
  },
  async resumeCampaign(campaignId: string) {
    const { data } = await apiClient.post<ApiSuccess<{ campaign: AdCampaign }>>(`/vendor/ad-campaigns/${campaignId}/resume`);
    return data.data.campaign;
  },
  async cancelCampaign(campaignId: string) {
    const { data } = await apiClient.post<ApiSuccess<{ campaign: AdCampaign }>>(`/vendor/ad-campaigns/${campaignId}/cancel`);
    return data.data.campaign;
  },

  // --- Admin moderation ---
  async listAllCampaigns(status?: string) {
    const { data } = await apiClient.get<ApiSuccess<{ campaigns: AdCampaign[] }>>(
      "/admin/ad-campaigns", { params: status ? { status } : undefined }
    );
    return data.data.campaigns;
  },
  async approveCampaign(campaignId: string) {
    const { data } = await apiClient.post<ApiSuccess<{ campaign: AdCampaign }>>(`/admin/ad-campaigns/${campaignId}/approve`);
    return data.data.campaign;
  },
  async rejectCampaign(campaignId: string, reason: string) {
    const { data } = await apiClient.post<ApiSuccess<{ campaign: AdCampaign }>>(`/admin/ad-campaigns/${campaignId}/reject`, { reason });
    return data.data.campaign;
  },
  async adminPauseCampaign(campaignId: string) {
    const { data } = await apiClient.post<ApiSuccess<{ campaign: AdCampaign }>>(`/admin/ad-campaigns/${campaignId}/pause`);
    return data.data.campaign;
  },
};
