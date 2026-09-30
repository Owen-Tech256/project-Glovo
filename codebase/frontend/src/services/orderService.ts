import { apiClient } from "./apiClient";
import type { ApiSuccess } from "../types/auth";
import type { Order, OrderStatusHistoryEntry, CheckoutResult, CheckoutSummary, Pagination } from "../types/order";

export const orderService = {
  // --- Checkout preview ---
  async validateCheckout(branchId: string, addressId: string) {
    const { data } = await apiClient.post<ApiSuccess<CheckoutResult>>("/checkout/validate", {
      branch_id: branchId,
      address_id: addressId,
    });
    return data.data;
  },
  async getCheckoutSummary(branchId: string, addressId: string) {
    const { data } = await apiClient.get<ApiSuccess<CheckoutSummary>>("/checkout/summary", {
      params: { branch_id: branchId, address_id: addressId },
    });
    return data.data;
  },

  // --- Customer orders ---
  async createOrder(branchId: string, addressId: string, idempotencyKey: string) {
    const { data } = await apiClient.post<ApiSuccess<{ order: Order }>>("/orders", {
      branch_id: branchId,
      address_id: addressId,
      idempotency_key: idempotencyKey,
    });
    return data.data.order;
  },
  async listMyOrders(status?: string, page = 1) {
    const { data } = await apiClient.get<ApiSuccess<{ orders: Order[]; pagination: Pagination }>>("/orders", {
      params: { status: status || undefined, page },
    });
    return data.data;
  },
  async getMyOrder(orderId: string) {
    const { data } = await apiClient.get<ApiSuccess<{ order: Order }>>(`/orders/${orderId}`);
    return data.data.order;
  },
  async cancelOrder(orderId: string, reason?: string) {
    const { data } = await apiClient.post<ApiSuccess<{ order: Order }>>(`/orders/${orderId}/cancel`, {
      reason: reason || undefined,
    });
    return data.data.order;
  },
  async getMyOrderStatusHistory(orderId: string) {
    const { data } = await apiClient.get<ApiSuccess<{ history: OrderStatusHistoryEntry[] }>>(
      `/orders/${orderId}/status-history`
    );
    return data.data.history;
  },

  // --- Vendor order queue ---
  async listVendorOrders(params: { status?: string; branchId?: string; page?: number }) {
    const { data } = await apiClient.get<ApiSuccess<{ orders: Order[]; pagination: Pagination }>>("/vendor/orders", {
      params: { status: params.status || undefined, branch_id: params.branchId || undefined, page: params.page ?? 1 },
    });
    return data.data;
  },
  async getVendorOrder(orderId: string) {
    const { data } = await apiClient.get<ApiSuccess<{ order: Order }>>(`/vendor/orders/${orderId}`);
    return data.data.order;
  },
  async transitionVendorOrder(orderId: string, toStatus: string, reason?: string) {
    const { data } = await apiClient.post<ApiSuccess<{ order: Order }>>(`/vendor/orders/${orderId}/transition`, {
      to_status: toStatus,
      reason: reason || undefined,
    });
    return data.data.order;
  },
  async getVendorOrderStatusHistory(orderId: string) {
    const { data } = await apiClient.get<ApiSuccess<{ history: OrderStatusHistoryEntry[] }>>(
      `/vendor/orders/${orderId}/status-history`
    );
    return data.data.history;
  },

  // --- Admin oversight (read-only) ---
  async listAllOrders(params: { status?: string; branchId?: string; customerId?: string; page?: number }) {
    const { data } = await apiClient.get<ApiSuccess<{ orders: Order[]; pagination: Pagination }>>("/admin/orders", {
      params: {
        status: params.status || undefined,
        branch_id: params.branchId || undefined,
        customer_id: params.customerId || undefined,
        page: params.page ?? 1,
      },
    });
    return data.data;
  },
  async getAnyOrder(orderId: string) {
    const { data } = await apiClient.get<ApiSuccess<{ order: Order }>>(`/admin/orders/${orderId}`);
    return data.data.order;
  },
  async getAnyOrderStatusHistory(orderId: string) {
    const { data } = await apiClient.get<ApiSuccess<{ history: OrderStatusHistoryEntry[] }>>(
      `/admin/orders/${orderId}/status-history`
    );
    return data.data.history;
  },
};
