export interface AdminPermission {
  key: string;
  description: string;
}

export interface AdminRole {
  id: string;
  name: string;
  description: string | null;
  is_system: boolean;
  status: "ACTIVE" | "DISABLED";
  staff_count: number;
  created_at: string;
  permissions?: string[];
}

export interface AuditEvent {
  id: number;
  actor: { id: string; name: string } | null;
  action: string;
  entity_type: string | null;
  entity_id: string | null;
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
  metadata: Record<string, unknown> | null;
  ip_address: string | null;
  created_at: string;
}
