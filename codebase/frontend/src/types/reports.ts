export type ReportType =
  | "ORDERS"
  | "FINANCE"
  | "VENDORS"
  | "RIDERS"
  | "DELIVERY"
  | "CUSTOMERS"
  | "PROMOTIONS_ADS"
  | "SUPPORT_DISPUTES";

export interface ReportDefinition {
  id: string;
  name: string;
  report_type: ReportType;
  configuration: Record<string, unknown>;
  access_level: string;
  created_by: string | null;
  created_at: string;
}

export type ReportExportStatus = "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";

export interface ReportExport {
  id: string;
  report_definition_id: string | null;
  report_type: string;
  requested_by: string | null;
  filters: Record<string, unknown>;
  row_count: number | null;
  status: ReportExportStatus;
  error_message: string | null;
  downloadable: boolean;
  completed_at: string | null;
  created_at: string;
}
