import { apiClient } from "./apiClient";
import type { ApiSuccess } from "../types/auth";
import type {
  Rider,
  RiderDocument,
  RiderZone,
  AvailabilityHistoryEntry,
  RiderLocationInfo,
  Delivery,
  DeliveryOffer,
  DeliveryTracking,
  DeliveryStatusHistoryEntry,
  PaginationMeta,
  DispatchHealth,
} from "../types/logistics";

export const logisticsService = {
  // --- Rider self-service ---

  async getMe() {
    const { data } = await apiClient.get<ApiSuccess<{ rider: Rider }>>("/rider/me");
    return data.data.rider;
  },

  async updateProfile(payload: { vehicle_type: string; registration_reference?: string | null }) {
    const { data } = await apiClient.patch<ApiSuccess<{ rider: Rider }>>("/rider/profile", payload);
    return data.data.rider;
  },

  async listDocuments() {
    const { data } = await apiClient.get<ApiSuccess<{ documents: RiderDocument[] }>>("/rider/documents");
    return data.data.documents;
  },

  async submitDocument(payload: { document_type: string; reference: string; expiry_date?: string | null }) {
    const { data } = await apiClient.post<ApiSuccess<{ document: RiderDocument }>>("/rider/documents", payload);
    return data.data.document;
  },

  async getAvailability() {
    const { data } = await apiClient.get<
      ApiSuccess<{ operational_status: string; history: AvailabilityHistoryEntry[] }>
    >("/rider/availability");
    return data.data;
  },

  async setAvailability(status: "OFFLINE" | "AVAILABLE", reason?: string) {
    const { data } = await apiClient.patch<ApiSuccess<{ rider: Rider }>>("/rider/availability", { status, reason });
    return data.data.rider;
  },

  async postLocation(latitude: number, longitude: number, accuracy_meters?: number) {
    const { data } = await apiClient.post<ApiSuccess<{ location: RiderLocationInfo }>>("/rider/location", {
      latitude,
      longitude,
      accuracy_meters,
    });
    return data.data.location;
  },

  async getLocation() {
    const { data } = await apiClient.get<ApiSuccess<{ location: RiderLocationInfo }>>("/rider/location");
    return data.data.location;
  },

  async listZones() {
    const { data } = await apiClient.get<ApiSuccess<{ zones: RiderZone[] }>>("/rider/zones");
    return data.data.zones;
  },

  async joinZone(zoneId: string) {
    const { data } = await apiClient.post<ApiSuccess<{ zone: RiderZone }>>("/rider/zones", { zone_id: zoneId });
    return data.data.zone;
  },

  async leaveZone(zoneId: string) {
    await apiClient.delete(`/rider/zones/${zoneId}`);
  },

  async listOffers() {
    const { data } = await apiClient.get<ApiSuccess<{ offers: DeliveryOffer[] }>>("/rider/delivery-offers");
    return data.data.offers;
  },

  async acceptOffer(assignmentId: string) {
    const { data } = await apiClient.post<ApiSuccess<{ delivery: Delivery }>>(
      `/rider/delivery-offers/${assignmentId}/accept`
    );
    return data.data.delivery;
  },

  async rejectOffer(assignmentId: string, reason?: string) {
    await apiClient.post(`/rider/delivery-offers/${assignmentId}/reject`, { reason });
  },

  async getCurrentDelivery() {
    const { data } = await apiClient.get<ApiSuccess<{ delivery: Delivery | null }>>("/rider/deliveries/current");
    return data.data.delivery;
  },

  // --- Delivery actions (rider) ---

  async pickup(deliveryId: string, reason?: string) {
    const { data } = await apiClient.post<ApiSuccess<{ delivery: Delivery }>>(
      `/deliveries/${deliveryId}/pickup`,
      { reason }
    );
    return data.data.delivery;
  },

  async startDelivering(deliveryId: string, reason?: string) {
    const { data } = await apiClient.post<ApiSuccess<{ delivery: Delivery }>>(
      `/deliveries/${deliveryId}/start`,
      { reason }
    );
    return data.data.delivery;
  },

  async complete(deliveryId: string, reason?: string) {
    const { data } = await apiClient.post<ApiSuccess<{ delivery: Delivery }>>(
      `/deliveries/${deliveryId}/complete`,
      { reason }
    );
    return data.data.delivery;
  },

  // --- Tracking (shared: customer / vendor / rider / admin) ---

  async getTracking(deliveryId: string) {
    const { data } = await apiClient.get<ApiSuccess<DeliveryTracking>>(`/deliveries/${deliveryId}/tracking`);
    return data.data;
  },

  async getStatusHistory(deliveryId: string) {
    const { data } = await apiClient.get<ApiSuccess<{ status_history: DeliveryStatusHistoryEntry[] }>>(
      `/deliveries/${deliveryId}/status-history`
    );
    return data.data.status_history;
  },

  async getOrderDelivery(orderId: string) {
    const { data } = await apiClient.get<ApiSuccess<DeliveryTracking>>(`/orders/${orderId}/delivery`);
    return data.data;
  },

  async getVendorOrderDelivery(orderId: string) {
    const { data } = await apiClient.get<ApiSuccess<DeliveryTracking>>(`/vendor/orders/${orderId}/delivery`);
    return data.data;
  },

  // --- Admin ---

  async adminListRiders(status?: string, page = 1) {
    const params = new URLSearchParams();
    if (status) params.set("status", status);
    params.set("page", String(page));
    const { data } = await apiClient.get<ApiSuccess<{ riders: Rider[]; pagination: PaginationMeta }>>(
      `/admin/riders?${params.toString()}`
    );
    return data.data;
  },

  async adminGetRider(riderId: string) {
    const { data } = await apiClient.get<ApiSuccess<{ rider: Rider }>>(`/admin/riders/${riderId}`);
    return data.data.rider;
  },

  async adminSetRiderStatus(riderId: string, status: string, reason?: string) {
    const { data } = await apiClient.patch<ApiSuccess<{ rider: Rider }>>(`/admin/riders/${riderId}/status`, {
      status,
      reason,
    });
    return data.data.rider;
  },

  async adminListRiderDocuments(riderId: string) {
    const { data } = await apiClient.get<ApiSuccess<{ documents: RiderDocument[] }>>(
      `/admin/riders/${riderId}/documents`
    );
    return data.data.documents;
  },

  async adminReviewDocument(
    riderId: string,
    documentId: string,
    verification_status: "VERIFIED" | "REJECTED",
    review_notes?: string
  ) {
    const { data } = await apiClient.patch<ApiSuccess<{ document: RiderDocument }>>(
      `/admin/riders/${riderId}/documents/${documentId}`,
      { verification_status, review_notes }
    );
    return data.data.document;
  },

  async adminListDeliveries(filters: { status?: string; page?: number } = {}) {
    const params = new URLSearchParams();
    if (filters.status) params.set("status", filters.status);
    params.set("page", String(filters.page ?? 1));
    const { data } = await apiClient.get<ApiSuccess<{ deliveries: Delivery[]; pagination: PaginationMeta }>>(
      `/admin/deliveries?${params.toString()}`
    );
    return data.data;
  },

  async adminGetDelivery(deliveryId: string) {
    const { data } = await apiClient.get<ApiSuccess<{ delivery: Delivery }>>(`/admin/deliveries/${deliveryId}`);
    return data.data.delivery;
  },

  async adminGetDispatchHealth() {
    const { data } = await apiClient.get<ApiSuccess<{ dispatch_health: DispatchHealth }>>(
      "/admin/logistics/dispatch-health"
    );
    return data.data.dispatch_health;
  },

  async adminReassignDelivery(deliveryId: string, reason?: string) {
    const { data } = await apiClient.post<ApiSuccess<{ delivery: Delivery }>>(
      `/admin/deliveries/${deliveryId}/reassign`,
      { reason }
    );
    return data.data.delivery;
  },
};
