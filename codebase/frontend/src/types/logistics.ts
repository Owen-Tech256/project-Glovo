export type RiderOnboardingStatus = "PENDING" | "UNDER_REVIEW" | "APPROVED" | "REJECTED" | "SUSPENDED";
export type RiderOperationalStatus = "OFFLINE" | "AVAILABLE" | "BUSY";
export type RiderVehicleType = "BICYCLE" | "SCOOTER" | "MOTORCYCLE" | "CAR" | "ON_FOOT";
export type RiderDocumentType =
  | "GOVERNMENT_ID"
  | "DRIVERS_LICENSE"
  | "VEHICLE_REGISTRATION"
  | "INSURANCE"
  | "BACKGROUND_CHECK"
  | "OTHER";
export type RiderDocumentVerificationStatus = "PENDING" | "VERIFIED" | "REJECTED";

export type DeliveryStatus =
  | "CREATED"
  | "SEARCHING"
  | "OFFERED"
  | "ASSIGNED"
  | "PICKED_UP"
  | "DELIVERING"
  | "DELIVERED"
  | "CANCELLED";

export type DeliveryOfferStatus = "OFFERED" | "ACCEPTED" | "REJECTED" | "EXPIRED" | "CANCELLED";

export interface RiderVehicle {
  id: string;
  vehicle_type: RiderVehicleType;
  registration_reference: string | null;
  status: "ACTIVE" | "INACTIVE";
  created_at: string;
  updated_at: string;
}

export interface Rider {
  id: string;
  user_id: string;
  full_name: string | null;
  onboarding_status: RiderOnboardingStatus;
  operational_status: RiderOperationalStatus;
  approved_at: string | null;
  location_updated_at: string | null;
  created_at: string;
  updated_at: string;
  vehicle?: RiderVehicle | null;
  documents?: RiderDocument[];
}

export interface RiderDocument {
  id: string;
  document_type: RiderDocumentType;
  reference: string;
  expiry_date: string | null;
  verification_status: RiderDocumentVerificationStatus;
  reviewed_by: string | null;
  reviewed_at: string | null;
  review_notes: string | null;
  created_at: string;
}

export interface RiderZone {
  id: string;
  zone_id: string;
  zone_name: string | null;
  branch_id: string | null;
  branch_name: string | null;
  status: "ACTIVE" | "INACTIVE";
  created_at: string;
}

export interface AvailabilityHistoryEntry {
  from_status: string | null;
  to_status: string;
  reason: string | null;
  changed_at: string;
}

export interface RiderLocationInfo {
  latitude: number | null;
  longitude: number | null;
  recorded_at: string | null;
  is_fresh: boolean;
}

export interface Delivery {
  id: string;
  order_id: string;
  order_number?: string | null;
  order_status?: string;
  branch_id: string;
  branch_name: string | null;
  rider_id: string | null;
  rider_name: string | null;
  status: DeliveryStatus;
  pickup_latitude: number;
  pickup_longitude: number;
  destination_latitude: number;
  destination_longitude: number;
  assigned_at: string | null;
  picked_up_at: string | null;
  delivered_at: string | null;
  cancelled_at: string | null;
  cancellation_reason: string | null;
  created_at: string;
  updated_at: string;
  status_history?: DeliveryStatusHistoryEntry[];
}

export interface DeliveryStatusHistoryEntry {
  from_status: string | null;
  to_status: string;
  changed_by: string | null;
  changed_by_role: string | null;
  reason: string | null;
  created_at: string;
}

export interface DeliveryOffer {
  id: string;
  delivery_id: string;
  status: DeliveryOfferStatus;
  offered_at: string;
  expires_at: string;
  responded_at: string | null;
  rejection_reason: string | null;
}

export interface TrackedLocation {
  latitude: number;
  longitude: number;
  accuracy_meters: number | null;
  recorded_at: string;
  is_stale: boolean;
}

export interface DeliveryTracking {
  delivery: Delivery;
  rider_location: TrackedLocation | null;
}

export interface PaginationMeta {
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
}

export interface DispatchHealth {
  searching_count: number;
  offered_count: number;
  stuck_count: number;
  stuck_threshold_seconds: number;
  stuck_deliveries: Delivery[];
}
