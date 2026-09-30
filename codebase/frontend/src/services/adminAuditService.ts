import { apiClient } from "./apiClient";
import type { ApiSuccess } from "../types/auth";
import type { AuditEvent } from "../types/admin";
import type { Pagination } from "../types/support";

export const adminAuditService = {
  async listEvents(filters: { entity_type?: string; entity_id?: string; user_id?: string; action?: string; page?: number }) {
    const { data } = await apiClient.get<ApiSuccess<{ events: AuditEvent[]; pagination: Pagination }>>(
      "/admin/audit/events",
      { params: filters }
    );
    return data.data;
  },
};
