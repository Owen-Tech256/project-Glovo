import { apiClient } from "./apiClient";
import type { ApiSuccess } from "../types/auth";
import type { CustomerAddress } from "../types/catalog";

export interface AddressInput {
  label: string;
  recipient_name: string;
  phone: string;
  address_line1: string;
  address_line2?: string | null;
  city: string;
  state?: string | null;
  postal_code?: string | null;
  country: string;
  latitude: number;
  longitude: number;
  delivery_instructions?: string | null;
  is_default?: boolean;
}

export const addressService = {
  async list() {
    const { data } = await apiClient.get<ApiSuccess<{ addresses: CustomerAddress[] }>>("/addresses");
    return data.data.addresses;
  },
  async create(payload: AddressInput) {
    const { data } = await apiClient.post<ApiSuccess<{ address: CustomerAddress }>>("/addresses", payload);
    return data.data.address;
  },
  async update(addressId: string, payload: Partial<AddressInput>) {
    const { data } = await apiClient.patch<ApiSuccess<{ address: CustomerAddress }>>(
      `/addresses/${addressId}`,
      payload
    );
    return data.data.address;
  },
  async remove(addressId: string) {
    await apiClient.delete(`/addresses/${addressId}`);
  },
};
