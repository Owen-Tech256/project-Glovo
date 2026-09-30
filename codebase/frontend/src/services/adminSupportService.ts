import { apiClient } from "./apiClient";
import type { ApiSuccess } from "../types/auth";
import type { SupportTicket, SupportMessage, SupportAttachment, Pagination } from "../types/support";

export interface TicketFilters {
  status?: string;
  category?: string;
  priority?: string;
  agent_id?: string;
  unassigned?: boolean;
  page?: number;
}

export const adminSupportService = {
  async listTickets(filters: TicketFilters) {
    const { data } = await apiClient.get<ApiSuccess<{ tickets: SupportTicket[]; pagination: Pagination }>>(
      "/admin/support/tickets",
      { params: { ...filters, unassigned: filters.unassigned ? "true" : undefined } }
    );
    return data.data;
  },

  async getTicket(ticketId: string) {
    const { data } = await apiClient.get<ApiSuccess<{ ticket: SupportTicket }>>(`/admin/support/tickets/${ticketId}`);
    return data.data.ticket;
  },

  async assign(ticketId: string, agentId: string | null) {
    const { data } = await apiClient.post<ApiSuccess<{ ticket: SupportTicket }>>(
      `/admin/support/tickets/${ticketId}/assign`,
      { agent_id: agentId }
    );
    return data.data.ticket;
  },

  async reply(ticketId: string, body: string, visibility: "PUBLIC" | "INTERNAL" = "PUBLIC") {
    const { data } = await apiClient.post<ApiSuccess<{ message: SupportMessage }>>(
      `/admin/support/tickets/${ticketId}/messages`,
      { body, visibility }
    );
    return data.data.message;
  },

  async addAttachment(ticketId: string, filename: string, reference: string, contentType?: string) {
    const { data } = await apiClient.post<ApiSuccess<{ attachment: SupportAttachment }>>(
      `/admin/support/tickets/${ticketId}/attachments`,
      { filename, reference, content_type: contentType }
    );
    return data.data.attachment;
  },

  async updateStatus(ticketId: string, status: string, resolutionSummary?: string) {
    const { data } = await apiClient.patch<ApiSuccess<{ ticket: SupportTicket }>>(
      `/admin/support/tickets/${ticketId}/status`,
      { status, resolution_summary: resolutionSummary }
    );
    return data.data.ticket;
  },
};
