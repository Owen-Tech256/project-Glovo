import { apiClient } from "./apiClient";
import type { ApiSuccess } from "../types/auth";
import type { ReportDefinition, ReportExport } from "../types/reports";
import type { Pagination } from "../types/support";

export const reportsService = {
  async listDefinitions() {
    const { data } = await apiClient.get<ApiSuccess<{ report_definitions: ReportDefinition[] }>>("/reports");
    return data.data.report_definitions;
  },

  async createDefinition(name: string, reportType: string, accessLevel = "analytics.view") {
    const { data } = await apiClient.post<ApiSuccess<{ report_definition: ReportDefinition }>>("/reports", {
      name,
      report_type: reportType,
      access_level: accessLevel,
    });
    return data.data.report_definition;
  },

  async listExports(page = 1) {
    const { data } = await apiClient.get<ApiSuccess<{ exports: ReportExport[]; pagination: Pagination }>>(
      "/reports/exports",
      { params: { page } }
    );
    return data.data;
  },

  async requestExport(payload: {
    report_type?: string;
    report_definition_id?: string;
    date_from?: string;
    date_to?: string;
  }) {
    const { data } = await apiClient.post<ApiSuccess<{ export: ReportExport }>>("/reports/exports", payload);
    return data.data.export;
  },

  downloadUrl(exportId: string) {
    return `/reports/exports/${exportId}/download`;
  },

  async download(exportId: string) {
    const response = await apiClient.get(`/reports/exports/${exportId}/download`, { responseType: "blob" });
    return response.data as Blob;
  },
};
