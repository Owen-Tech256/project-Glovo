import { apiClient } from "./apiClient";
import type { ApiSuccess } from "../types/auth";
import type { SupportTicket, SupportMessage, SupportAttachment, Pagination } from "../types/support";

export const supportService = {
  async createTicket(payload: {
    category: string;
    subject: string;
    message: string;
    priority?: string;
    related_entity_type?: string;
    related_entity_id?: string;
  }) {
    const { data } = await apiClient.post<ApiSuccess<{ ticket: SupportTicket }>>("/support/tickets", payload);
    return data.data.ticket;
  },

  async listMyTickets(status?: string, page = 1) {
    const { data } = await apiClient.get<ApiSuccess<{ tickets: SupportTicket[]; pagination: Pagination }>>(
      "/support/tickets",
      { params: { status: status || undefined, page } }
    );
    return data.data;
  },

  async getTicket(ticketId: string) {
    const { data } = await apiClient.get<ApiSuccess<{ ticket: SupportTicket }>>(`/support/tickets/${ticketId}`);
    return data.data.ticket;
  },

  async reply(ticketId: string, body: string) {
    const { data } = await apiClient.post<ApiSuccess<{ message: SupportMessage }>>(
      `/support/tickets/${ticketId}/messages`,
      { body }
    );
    return data.data.message;
  },

  async addAttachment(ticketId: string, filename: string, reference: string, contentType?: string) {
    const { data } = await apiClient.post<ApiSuccess<{ attachment: SupportAttachment }>>(
      `/support/tickets/${ticketId}/attachments`,
      { filename, reference, content_type: contentType }
    );
    return data.data.attachment;
  },
};
