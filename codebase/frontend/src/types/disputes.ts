import type { TicketParty } from "./support";

export type DisputeCategory =
  | "MISSING_ITEM"
  | "WRONG_ITEM"
  | "DAMAGED_ITEM"
  | "LATE_DELIVERY"
  | "FAILED_DELIVERY"
  | "PAYMENT_ISSUE"
  | "SERVICE_COMPLAINT"
  | "OTHER";

export type DisputePriority = "LOW" | "NORMAL" | "HIGH" | "URGENT";

export type DisputeStatus = "OPEN" | "INVESTIGATING" | "ACTION_REQUIRED" | "RESOLVED" | "REJECTED" | "CLOSED";

export type DisputeActionType =
  | "NOTE"
  | "REQUEST_INFO"
  | "REFUND_ISSUED"
  | "PARTIAL_REFUND_ISSUED"
  | "REPLACEMENT_APPROVED"
  | "ESCALATED"
  | "REJECTED"
  | "RESOLVED"
  | "REOPENED"
  | "OTHER";

export interface DisputeEvidence {
  id: string;
  submitted_by: TicketParty | null;
  evidence_type: string;
  secure_reference: string | null;
  description: string | null;
  created_at: string;
}

export interface DisputeAction {
  id: string;
  action_type: DisputeActionType;
  actor: TicketParty | null;
  reference_type: string | null;
  reference_id: string | null;
  reason: string | null;
  status: "COMPLETED" | "FAILED";
  created_at: string;
}

export interface Dispute {
  id: string;
  dispute_number: string;
  ticket_id: string | null;
  order: { id: string; number: string } | null;
  delivery_id: string | null;
  payment_id: string | null;
  refund_id: string | null;
  opened_by: TicketParty | null;
  category: DisputeCategory;
  priority: DisputePriority;
  status: DisputeStatus;
  description: string;
  resolution: string | null;
  resolved_by: string | null;
  resolved_at: string | null;
  created_at: string;
  updated_at: string;
  evidence?: DisputeEvidence[];
  actions?: DisputeAction[];
}
