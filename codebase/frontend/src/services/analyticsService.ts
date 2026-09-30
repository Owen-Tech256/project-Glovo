import { apiClient } from "./apiClient";
import type { ApiSuccess } from "../types/auth";
import type {
  AnalyticsOverview,
  OrdersMetrics,
  FinanceMetrics,
  DeliveryMetrics,
  CustomerMetrics,
  PromotionAdMetrics,
  SupportDisputeMetrics,
} from "../types/analytics";

export interface DateRange {
  date_from?: string;
  date_to?: string;
}

export const analyticsService = {
  async overview(range: DateRange) {
    const { data } = await apiClient.get<ApiSuccess<AnalyticsOverview>>("/analytics/overview", { params: range });
    return data.data;
  },
  async orders(range: DateRange) {
    const { data } = await apiClient.get<ApiSuccess<OrdersMetrics>>("/analytics/orders", { params: range });
    return data.data;
  },
  async finance(range: DateRange) {
    const { data } = await apiClient.get<ApiSuccess<FinanceMetrics>>("/analytics/finance", { params: range });
    return data.data;
  },
  async vendors(range: DateRange) {
    const { data } = await apiClient.get<ApiSuccess<{ vendors: import("../types/analytics").VendorMetricRow[] }>>(
      "/analytics/vendors",
      { params: range }
    );
    return data.data.vendors;
  },
  async riders(range: DateRange) {
    const { data } = await apiClient.get<ApiSuccess<{ riders: import("../types/analytics").RiderMetricRow[] }>>(
      "/analytics/riders",
      { params: range }
    );
    return data.data.riders;
  },
  async delivery(range: DateRange) {
    const { data } = await apiClient.get<ApiSuccess<DeliveryMetrics>>("/analytics/delivery", { params: range });
    return data.data;
  },
  async customers(range: DateRange) {
    const { data } = await apiClient.get<ApiSuccess<CustomerMetrics>>("/analytics/customers", { params: range });
    return data.data;
  },
  async promotionsAds(range: DateRange) {
    const { data } = await apiClient.get<ApiSuccess<PromotionAdMetrics>>("/analytics/promotions-ads", { params: range });
    return data.data;
  },
  async supportDisputes(range: DateRange) {
    const { data } = await apiClient.get<ApiSuccess<SupportDisputeMetrics>>("/analytics/support-disputes", {
      params: range,
    });
    return data.data;
  },
};
