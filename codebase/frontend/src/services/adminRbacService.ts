import { apiClient } from "./apiClient";
import type { ApiSuccess, User } from "../types/auth";
import type { AdminRole, AdminPermission } from "../types/admin";
import type { Pagination } from "../types/support";

export const adminRbacService = {
  async listPermissions() {
    const { data } = await apiClient.get<ApiSuccess<{ permissions: AdminPermission[] }>>("/admin/permissions");
    return data.data.permissions;
  },

  async listRoles() {
    const { data } = await apiClient.get<ApiSuccess<{ roles: AdminRole[] }>>("/admin/roles");
    return data.data.roles;
  },

  async createRole(name: string, description: string, permissionKeys: string[]) {
    const { data } = await apiClient.post<ApiSuccess<{ role: AdminRole }>>("/admin/roles", {
      name,
      description,
      permission_keys: permissionKeys,
    });
    return data.data.role;
  },

  async updateRole(roleId: string, changes: { description?: string; permission_keys?: string[]; status?: string }) {
    const { data } = await apiClient.patch<ApiSuccess<{ role: AdminRole }>>(`/admin/roles/${roleId}`, changes);
    return data.data.role;
  },

  async listStaff(roleId?: string, page = 1) {
    const { data } = await apiClient.get<ApiSuccess<{ staff: User[]; pagination: Pagination }>>("/admin/staff", {
      params: { role_id: roleId || undefined, page },
    });
    return data.data;
  },

  async assignStaffRole(userId: string, roleId: string | null) {
    const { data } = await apiClient.patch<ApiSuccess<{ staff: User }>>(`/admin/staff/${userId}/role`, {
      role_id: roleId,
    });
    return data.data.staff;
  },
};
