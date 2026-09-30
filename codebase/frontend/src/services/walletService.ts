import { apiClient } from "./apiClient";
import type { ApiSuccess } from "../types/auth";
import type { RiderWallet, WalletTransaction, Pagination } from "../types/payments";

export const walletService = {
  async getWallet() {
    const { data } = await apiClient.get<ApiSuccess<{ wallet: RiderWallet }>>("/rider/wallet");
    return data.data.wallet;
  },
  async listTransactions(page = 1) {
    const { data } = await apiClient.get<ApiSuccess<{ transactions: WalletTransaction[]; pagination: Pagination }>>(
      "/rider/wallet/transactions",
      { params: { page } }
    );
    return data.data;
  },
};
