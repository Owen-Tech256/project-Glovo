export type VendorStatus = "ACTIVE" | "SUSPENDED" | "DISABLED";
export type BranchStatus = "ACTIVE" | "SUSPENDED" | "CLOSED";
export type DeliveryZoneStatus = "ACTIVE" | "INACTIVE";
export type ProductStatus = "ACTIVE" | "ARCHIVED";
export type BranchProductAvailability = "AVAILABLE" | "UNAVAILABLE";

export interface Vendor {
  id: string;
  name: string;
  description: string | null;
  phone: string | null;
  email: string | null;
  logo_url: string | null;
  status: VendorStatus;
  owner_id?: string;
  created_at: string;
  updated_at: string;
}

export interface Branch {
  id: string;
  vendor_id: string;
  vendor_name?: string | null;
  vendor_rating_average?: number | null;
  vendor_rating_count?: number;
  name: string;
  address: string;
  latitude: number;
  longitude: number;
  phone: string | null;
  status: BranchStatus;
  created_at: string;
  updated_at: string;
  distance_meters?: number;
}

export interface DiscoveryPagination {
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
}

export interface DeliveryZone {
  id: string;
  branch_id: string;
  name: string;
  status: DeliveryZoneStatus;
  zone_type: "RADIUS" | "POLYGON";
  center_latitude: number | null;
  center_longitude: number | null;
  radius_meters: number | null;
  created_at: string;
  updated_at: string;
}

export interface Category {
  id: string;
  vendor_id: string;
  name: string;
  description: string | null;
  image_url: string | null;
  sort_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProductImage {
  id: string;
  product_id: string;
  image_url: string;
  alt_text: string | null;
  sort_order: number;
  created_at: string;
}

export interface Product {
  id: string;
  category_id: string;
  name: string;
  description: string | null;
  sku: string | null;
  price: string;
  status: ProductStatus;
  images?: ProductImage[];
  created_at: string;
  updated_at: string;
}

export interface BranchProduct {
  id: string;
  branch_id: string;
  product: Product;
  price_override: string | null;
  effective_price: string | null;
  availability_status: BranchProductAvailability;
  created_at: string;
  updated_at: string;
}

export interface CustomerAddress {
  id: string;
  label: string;
  recipient_name: string;
  phone: string;
  address_line1: string;
  address_line2: string | null;
  city: string;
  state: string | null;
  postal_code: string | null;
  country: string;
  latitude: number;
  longitude: number;
  delivery_instructions: string | null;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}
