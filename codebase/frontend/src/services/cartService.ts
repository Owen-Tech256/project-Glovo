import { apiClient } from "./apiClient";
import type { ApiSuccess } from "../types/auth";
import type { Cart } from "../types/cart";

export const cartService = {
  async listActiveCarts() {
    const { data } = await apiClient.get<ApiSuccess<{ carts: Cart[] }>>("/cart");
    return data.data.carts;
  },
  async getCartForBranch(branchId: string) {
    const { data } = await apiClient.get<ApiSuccess<{ cart: Cart }>>("/cart", { params: { branch_id: branchId } });
    return data.data.cart;
  },
  async addItem(branchId: string, productId: string, quantity = 1) {
    const { data } = await apiClient.post<ApiSuccess<{ cart: Cart }>>("/cart/items", {
      branch_id: branchId,
      product_id: productId,
      quantity,
    });
    return data.data.cart;
  },
  async updateItemQuantity(itemId: string, quantity: number) {
    const { data } = await apiClient.patch<ApiSuccess<{ cart: Cart }>>(`/cart/items/${itemId}`, { quantity });
    return data.data.cart;
  },
  async removeItem(itemId: string) {
    await apiClient.delete(`/cart/items/${itemId}`);
  },
  async clearCart(branchId?: string) {
    await apiClient.delete("/cart", { params: branchId ? { branch_id: branchId } : undefined });
  },
  async applyPromotion(branchId: string, code: string) {
    const { data } = await apiClient.post<ApiSuccess<{ cart: Cart }>>(
      "/cart/promotion", { code }, { params: { branch_id: branchId } }
    );
    return data.data.cart;
  },
  async removePromotion(branchId: string) {
    const { data } = await apiClient.delete<ApiSuccess<{ cart: Cart }>>(
      "/cart/promotion", { params: { branch_id: branchId } }
    );
    return data.data.cart;
  },
};
