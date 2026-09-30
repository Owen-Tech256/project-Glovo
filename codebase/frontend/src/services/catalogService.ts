import { apiClient } from "./apiClient";
import type { ApiSuccess } from "../types/auth";
import type { Category, Product, ProductImage, BranchProduct, Branch, DiscoveryPagination } from "../types/catalog";

export interface CategoryInput {
  name: string;
  description?: string | null;
  image_url?: string | null;
  sort_order?: number;
  is_active?: boolean;
}

export interface ProductInput {
  category_id: string;
  name: string;
  description?: string | null;
  sku?: string | null;
  price: string;
}

export const catalogService = {
  // --- Categories (vendor self-service) ---
  async listMyCategories() {
    const { data } = await apiClient.get<ApiSuccess<{ categories: Category[] }>>("/vendors/me/categories");
    return data.data.categories;
  },
  async createCategory(payload: CategoryInput) {
    const { data } = await apiClient.post<ApiSuccess<{ category: Category }>>("/vendors/me/categories", payload);
    return data.data.category;
  },
  async updateCategory(categoryId: string, payload: Partial<CategoryInput>) {
    const { data } = await apiClient.patch<ApiSuccess<{ category: Category }>>(
      `/vendors/me/categories/${categoryId}`,
      payload
    );
    return data.data.category;
  },
  async deactivateCategory(categoryId: string) {
    await apiClient.delete(`/vendors/me/categories/${categoryId}`);
  },

  // --- Products (vendor self-service) ---
  async listMyProducts() {
    const { data } = await apiClient.get<ApiSuccess<{ products: Product[] }>>("/vendors/me/products");
    return data.data.products;
  },
  async createProduct(payload: ProductInput) {
    const { data } = await apiClient.post<ApiSuccess<{ product: Product }>>("/vendors/me/products", payload);
    return data.data.product;
  },
  async updateProduct(productId: string, payload: Partial<ProductInput & { status: string }>) {
    const { data } = await apiClient.patch<ApiSuccess<{ product: Product }>>(
      `/vendors/me/products/${productId}`,
      payload
    );
    return data.data.product;
  },
  async archiveProduct(productId: string) {
    await apiClient.delete(`/vendors/me/products/${productId}`);
  },

  // --- Product images (vendor self-service) ---
  async addImage(productId: string, payload: { image_url: string; alt_text?: string | null; sort_order?: number }) {
    const { data } = await apiClient.post<ApiSuccess<{ image: ProductImage }>>(
      `/vendors/me/products/${productId}/images`,
      payload
    );
    return data.data.image;
  },
  async deleteImage(productId: string, imageId: string) {
    await apiClient.delete(`/vendors/me/products/${productId}/images/${imageId}`);
  },

  // --- Branch-product availability & pricing (vendor self-service) ---
  async listBranchProducts(branchId: string) {
    const { data } = await apiClient.get<ApiSuccess<{ branch_products: BranchProduct[] }>>(
      `/vendors/me/branches/${branchId}/products`
    );
    return data.data.branch_products;
  },
  async setBranchProduct(
    branchId: string,
    productId: string,
    payload: { price_override?: string | null; availability_status?: string }
  ) {
    const { data } = await apiClient.put<ApiSuccess<{ branch_product: BranchProduct }>>(
      `/vendors/me/branches/${branchId}/products/${productId}`,
      payload
    );
    return data.data.branch_product;
  },
  async removeBranchProduct(branchId: string, productId: string) {
    await apiClient.delete(`/vendors/me/branches/${branchId}/products/${productId}`);
  },

  // --- Public catalog browsing ---
  async listPublicCategories(vendorId: string) {
    const { data } = await apiClient.get<ApiSuccess<{ categories: Category[] }>>(`/vendors/${vendorId}/categories`);
    return data.data.categories;
  },
  async listPublicBranchProducts(branchId: string) {
    const { data } = await apiClient.get<ApiSuccess<{ branch_products: BranchProduct[] }>>(
      `/branches/${branchId}/products`
    );
    return data.data.branch_products;
  },

  // --- Discovery ---
  async discoverBranches(
    lat: number,
    lng: number,
    options?: { search?: string; sort?: "distance" | "rating" | "name"; minRating?: number; page?: number; perPage?: number }
  ) {
    const { data } = await apiClient.get<ApiSuccess<{ branches: Branch[]; pagination: DiscoveryPagination }>>(
      "/discovery/branches",
      {
        params: {
          lat,
          lng,
          search: options?.search || undefined,
          sort: options?.sort,
          min_rating: options?.minRating,
          page: options?.page,
          per_page: options?.perPage,
        },
      }
    );
    return data.data;
  },
};
