import { apiClient } from "./apiClient";
import type { ApiSuccess } from "../types/auth";
import type { Vendor, Branch, DeliveryZone } from "../types/catalog";

export interface BranchInput {
  name: string;
  address: string;
  latitude: number;
  longitude: number;
  phone?: string | null;
}

export interface ZoneInput {
  name: string;
  center_latitude: number;
  center_longitude: number;
  radius_meters: number;
}

export const vendorService = {
  async getMyVendor() {
    const { data } = await apiClient.get<ApiSuccess<{ vendor: Vendor }>>("/vendors/me");
    return data.data.vendor;
  },

  async updateMyVendor(payload: Partial<Pick<Vendor, "name" | "description" | "phone" | "email" | "logo_url">>) {
    const { data } = await apiClient.patch<ApiSuccess<{ vendor: Vendor }>>("/vendors/me", payload);
    return data.data.vendor;
  },

  async listMyBranches() {
    const { data } = await apiClient.get<ApiSuccess<{ branches: Branch[] }>>("/vendors/me/branches");
    return data.data.branches;
  },

  async createBranch(payload: BranchInput) {
    const { data } = await apiClient.post<ApiSuccess<{ branch: Branch }>>("/vendors/me/branches", payload);
    return data.data.branch;
  },

  async updateBranch(branchId: string, payload: Partial<BranchInput & { status: string }>) {
    const { data } = await apiClient.patch<ApiSuccess<{ branch: Branch }>>(
      `/vendors/me/branches/${branchId}`,
      payload
    );
    return data.data.branch;
  },

  async closeBranch(branchId: string) {
    await apiClient.delete(`/vendors/me/branches/${branchId}`);
  },

  async listZones(branchId: string) {
    const { data } = await apiClient.get<ApiSuccess<{ delivery_zones: DeliveryZone[] }>>(
      `/vendors/me/branches/${branchId}/zones`
    );
    return data.data.delivery_zones;
  },

  async createZone(branchId: string, payload: ZoneInput) {
    const { data } = await apiClient.post<ApiSuccess<{ delivery_zone: DeliveryZone }>>(
      `/vendors/me/branches/${branchId}/zones`,
      payload
    );
    return data.data.delivery_zone;
  },

  async updateZone(branchId: string, zoneId: string, payload: Partial<ZoneInput & { status: string }>) {
    const { data } = await apiClient.patch<ApiSuccess<{ delivery_zone: DeliveryZone }>>(
      `/vendors/me/branches/${branchId}/zones/${zoneId}`,
      payload
    );
    return data.data.delivery_zone;
  },

  async deleteZone(branchId: string, zoneId: string) {
    await apiClient.delete(`/vendors/me/branches/${branchId}/zones/${zoneId}`);
  },

  // --- Public browsing ---

  async getPublicVendor(vendorId: string) {
    const { data } = await apiClient.get<ApiSuccess<{ vendor: Vendor }>>(`/vendors/${vendorId}`);
    return data.data.vendor;
  },

  async listPublicVendorBranches(vendorId: string) {
    const { data } = await apiClient.get<ApiSuccess<{ branches: Branch[] }>>(`/vendors/${vendorId}/branches`);
    return data.data.branches;
  },
};
