import { apiClient } from "./apiClient";
import type { ApiSuccess } from "../types/auth";
import type { Review, ReviewableTarget, ReviewReport } from "../types/growth";

export const reviewService = {
  // --- Customer ---
  async getReviewableTargets(orderId: string) {
    const { data } = await apiClient.get<ApiSuccess<{ reviewable: ReviewableTarget[] }>>(`/orders/${orderId}/reviews`);
    return data.data.reviewable;
  },
  async submitReview(orderId: string, targetType: string, targetId: string, rating: number, body?: string) {
    const { data } = await apiClient.post<ApiSuccess<{ review: Review }>>(`/orders/${orderId}/reviews`, {
      target_type: targetType, target_id: targetId, rating, body,
    });
    return data.data.review;
  },
  async updateReview(reviewId: string, rating?: number, body?: string) {
    const { data } = await apiClient.patch<ApiSuccess<{ review: Review }>>(`/reviews/${reviewId}`, { rating, body });
    return data.data.review;
  },
  async withdrawReview(reviewId: string) {
    await apiClient.delete(`/reviews/${reviewId}`);
  },
  async reportReview(reviewId: string, reason: string) {
    await apiClient.post(`/reviews/${reviewId}/report`, { reason });
  },

  // --- Public ---
  async listVendorReviews(vendorId: string, page = 1) {
    const { data } = await apiClient.get<ApiSuccess<{ reviews: Review[] }>>(`/vendors/${vendorId}/reviews`, { params: { page } });
    return data.data.reviews;
  },

  // --- Vendor / rider self-management ---
  async listMyVendorReviews(page = 1) {
    const { data } = await apiClient.get<ApiSuccess<{ reviews: Review[] }>>("/vendor/reviews", { params: { page } });
    return data.data.reviews;
  },
  async listMyRiderReviews(page = 1) {
    const { data } = await apiClient.get<ApiSuccess<{ reviews: Review[] }>>("/rider/reviews", { params: { page } });
    return data.data.reviews;
  },
  async respondToReview(reviewId: string, body: string) {
    const { data } = await apiClient.post<ApiSuccess<{ review: Review }>>(`/reviews/${reviewId}/response`, { body });
    return data.data.review;
  },

  // --- Admin moderation ---
  async listAllReviews(status?: string) {
    const { data } = await apiClient.get<ApiSuccess<{ reviews: Review[] }>>("/admin/reviews", { params: status ? { status } : undefined });
    return data.data.reviews;
  },
  async moderateReview(reviewId: string, status: string) {
    const { data } = await apiClient.patch<ApiSuccess<{ review: Review }>>(`/admin/reviews/${reviewId}/moderate`, { status });
    return data.data.review;
  },
  async listReviewReports(status?: string) {
    const { data } = await apiClient.get<ApiSuccess<{ reports: ReviewReport[] }>>("/admin/review-reports", { params: status ? { status } : undefined });
    return data.data.reports;
  },
  async resolveReviewReport(reportId: string, status: "REVIEWED" | "DISMISSED", hideReview = false) {
    const { data } = await apiClient.patch<ApiSuccess<{ report: ReviewReport }>>(`/admin/review-reports/${reportId}`, {
      status, hide_review: hideReview,
    });
    return data.data.report;
  },
};
