import { apiClient } from "./apiClient";
import type { ApiSuccess } from "../types/auth";
import type { Payment, Refund } from "../types/payments";

export const paymentService = {
  // --- Customer payments ---
  async createPayment(orderId: string, method = "CARD", idempotencyKey?: string) {
    const { data } = await apiClient.post<ApiSuccess<{ payment: Payment }>>("/payments", {
      order_id: orderId,
      method,
      idempotency_key: idempotencyKey,
    });
    return data.data.payment;
  },
  async getPayment(paymentId: string) {
    const { data } = await apiClient.get<ApiSuccess<{ payment: Payment }>>(`/payments/${paymentId}`);
    return data.data.payment;
  },
  async verifyPayment(paymentId: string) {
    const { data } = await apiClient.post<ApiSuccess<{ payment: Payment }>>(`/payments/${paymentId}/verify`);
    return data.data.payment;
  },
  async listOrderPayments(orderId: string) {
    const { data } = await apiClient.get<ApiSuccess<{ payments: Payment[] }>>(`/orders/${orderId}/payments`);
    return data.data.payments;
  },

  // --- Customer refunds (order-scoped) ---
  async requestRefund(orderId: string, reason: string, amount?: string, idempotencyKey?: string) {
    const { data } = await apiClient.post<ApiSuccess<{ refund: Refund }>>(`/orders/${orderId}/refund-request`, {
      reason,
      amount,
      idempotency_key: idempotencyKey,
    });
    return data.data.refund;
  },
  async listOrderRefunds(orderId: string) {
    const { data } = await apiClient.get<ApiSuccess<{ refunds: Refund[] }>>(`/orders/${orderId}/refunds`);
    return data.data.refunds;
  },
};
