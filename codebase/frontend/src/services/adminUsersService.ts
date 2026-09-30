import { apiClient } from "./apiClient";
import type { ApiSuccess, User } from "../types/auth";
import type { Pagination } from "../types/support";

export interface UserDetail extends User {
  vendor?: { id: string; name: string; status: string };
  rider?: { id: string; onboarding_status: string; operational_status: string };
}

export const adminUsersService = {
  async listUsers(filters: { role?: string; status?: string; q?: string; page?: number }) {
    const { data } = await apiClient.get<ApiSuccess<{ users: User[]; pagination: Pagination }>>("/admin/users", {
      params: filters,
    });
    return data.data;
  },

  async getUser(userId: string) {
    const { data } = await apiClient.get<ApiSuccess<{ user: UserDetail }>>(`/admin/users/${userId}`);
    return data.data.user;
  },

  async updateStatus(userId: string, status: string, reason?: string) {
    const { data } = await apiClient.patch<ApiSuccess<{ user: User }>>(`/admin/users/${userId}/status`, {
      status,
      reason,
    });
    return data.data.user;
  },
};
