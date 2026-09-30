import { apiClient } from "./apiClient";
import type { ApiSuccess } from "../types/auth";
import type { Vendor, Branch, Category, Product } from "../types/catalog";

export interface PaginatedVendors {
  vendors: Vendor[];
  pagination: { page: number; per_page: number; total: number; total_pages: number };
}

export const adminCatalogService = {
  async listVendors(page = 1, status?: string) {
    const { data } = await apiClient.get<ApiSuccess<PaginatedVendors>>("/admin/vendors", {
      params: { page, status: status || undefined },
    });
    return data.data;
  },

  async getVendor(vendorId: string) {
    const { data } = await apiClient.get<ApiSuccess<{ vendor: Vendor; branch_count: number; category_count: number }>>(
      `/admin/vendors/${vendorId}`
    );
    return data.data;
  },

  async updateVendorStatus(vendorId: string, status: string) {
    const { data } = await apiClient.patch<ApiSuccess<{ vendor: Vendor }>>(`/admin/vendors/${vendorId}/status`, {
      status,
    });
    return data.data.vendor;
  },

  async listVendorBranches(vendorId: string) {
    const { data } = await apiClient.get<ApiSuccess<{ branches: Branch[] }>>(`/admin/vendors/${vendorId}/branches`);
    return data.data.branches;
  },

  async updateBranchStatus(branchId: string, status: string) {
    const { data } = await apiClient.patch<ApiSuccess<{ branch: Branch }>>(`/admin/branches/${branchId}/status`, {
      status,
    });
    return data.data.branch;
  },

  async getVendorCatalog(vendorId: string) {
    const { data } = await apiClient.get<ApiSuccess<{ categories: Array<Category & { products: Product[] }> }>>(
      `/admin/vendors/${vendorId}/catalog`
    );
    return data.data.categories;
  },
};
