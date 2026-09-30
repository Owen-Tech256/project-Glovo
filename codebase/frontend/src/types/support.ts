export type TicketCategory =
  | "ORDER_ISSUE"
  | "PAYMENT_ISSUE"
  | "DELIVERY_ISSUE"
  | "ACCOUNT_ISSUE"
  | "VENDOR_ISSUE"
  | "RIDER_ISSUE"
  | "GENERAL"
  | "OTHER";

export type TicketPriority = "LOW" | "NORMAL" | "HIGH" | "URGENT";

export type TicketStatus = "OPEN" | "IN_PROGRESS" | "WAITING_FOR_CUSTOMER" | "RESOLVED" | "CLOSED";

export type RelatedEntityType = "ORDER" | "DELIVERY" | "PAYMENT" | "REFUND" | "VENDOR" | "RIDER";

export type MessageVisibility = "PUBLIC" | "INTERNAL";

export interface TicketParty {
  id: string;
  name: string;
  role?: string;
}

export interface SupportMessage {
  id: string;
  sender: TicketParty | null;
  body: string;
  visibility: MessageVisibility;
  created_at: string;
}

export interface SupportAttachment {
  id: string;
  message_id: string | null;
  uploader: string | null;
  filename: string;
  content_type: string | null;
  reference: string;
  created_at: string;
}

export interface SupportTicket {
  id: string;
  ticket_number: string;
  requester: TicketParty | null;
  assigned_agent: TicketParty | null;
  category: TicketCategory;
  priority: TicketPriority;
  status: TicketStatus;
  subject: string;
  related_entity_type: RelatedEntityType | null;
  related_entity_id: string | null;
  resolution_summary: string | null;
  resolved_at: string | null;
  closed_at: string | null;
  created_at: string;
  updated_at: string;
  messages?: SupportMessage[];
  attachments?: SupportAttachment[];
}

export interface Pagination {
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
}
