import { apiClient } from "./apiClient";
import type { ApiSuccess } from "../types/auth";
import type { Promotion } from "../types/growth";

export interface PromotionInput {
  name: string;
  description?: string;
  code?: string;
  type: "PERCENTAGE" | "FIXED_AMOUNT" | "FREE_DELIVERY";
  value: string;
  max_discount_amount?: string;
  min_subtotal?: string;
  scope_type?: "ORDER" | "VENDOR" | "BRANCH" | "CATEGORY" | "PRODUCT";
  scope_target_ids?: string[];
  usage_limit_total?: number;
  usage_limit_per_customer?: number;
  status?: "DRAFT" | "ACTIVE" | "PAUSED" | "ARCHIVED";
  starts_at?: string;
  ends_at?: string;
}

export const promotionService = {
  // --- Customer discovery ---
  async listPublicPromotions() {
    const { data } = await apiClient.get<ApiSuccess<{ promotions: Promotion[] }>>("/promotions");
    return data.data.promotions;
  },

  // --- Vendor management ---
  async listVendorPromotions(status?: string) {
    const { data } = await apiClient.get<ApiSuccess<{ promotions: Promotion[] }>>(
      "/vendor/promotions", { params: status ? { status } : undefined }
    );
    return data.data.promotions;
  },
  async createVendorPromotion(input: PromotionInput) {
    const { data } = await apiClient.post<ApiSuccess<{ promotion: Promotion }>>("/vendor/promotions", input);
    return data.data.promotion;
  },
  async updateVendorPromotion(promotionId: string, input: Partial<PromotionInput>) {
    const { data } = await apiClient.patch<ApiSuccess<{ promotion: Promotion }>>(
      `/vendor/promotions/${promotionId}`, input
    );
    return data.data.promotion;
  },

  // --- Admin management ---
  async listAllPromotions(status?: string) {
    const { data } = await apiClient.get<ApiSuccess<{ promotions: Promotion[] }>>(
      "/admin/promotions", { params: status ? { status } : undefined }
    );
    return data.data.promotions;
  },
  async createAdminPromotion(input: PromotionInput & { vendor_id?: string }) {
    const { data } = await apiClient.post<ApiSuccess<{ promotion: Promotion }>>("/admin/promotions", input);
    return data.data.promotion;
  },
  async updateAdminPromotion(promotionId: string, input: Partial<PromotionInput>) {
    const { data } = await apiClient.patch<ApiSuccess<{ promotion: Promotion }>>(
      `/admin/promotions/${promotionId}`, input
    );
    return data.data.promotion;
  },
};
