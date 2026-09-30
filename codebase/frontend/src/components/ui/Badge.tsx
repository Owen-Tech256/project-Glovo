import type { ReactNode } from "react";

type Tone = "neutral" | "success" | "warning" | "danger" | "primary";

const toneClasses: Record<Tone, string> = {
  neutral: "bg-ink/[0.06] text-ink-soft",
  success: "bg-primary-soft text-primary-dark",
  warning: "bg-warning-soft text-warning",
  danger: "bg-danger-soft text-danger",
  primary: "bg-primary-soft text-primary-dark",
};

export function Badge({ tone = "neutral", children, icon }: { tone?: Tone; children: ReactNode; icon?: ReactNode }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${toneClasses[tone]}`}>
      {icon}
      {children}
    </span>
  );
}

const roleTone: Record<string, Tone> = {
  ACTIVE: "success",
  AVAILABLE: "success",
  SUSPENDED: "warning",
  INACTIVE: "neutral",
  UNAVAILABLE: "neutral",
  DISABLED: "danger",
  CLOSED: "danger",
  ARCHIVED: "neutral",
  // Order lifecycle (Phase 3)
  CREATED: "neutral",
  PENDING_PAYMENT: "warning",
  PAYMENT_CONFIRMED: "primary",
  VENDOR_ACCEPTED: "primary",
  PREPARING: "warning",
  READY: "success",
  CANCELLED: "danger",
  // Phase 4: order lifecycle continuation
  RIDER_ASSIGNED: "primary",
  PICKED_UP: "primary",
  DELIVERING: "warning",
  DELIVERED: "success",
  // Phase 4: delivery lifecycle
  SEARCHING: "warning",
  OFFERED: "primary",
  ASSIGNED: "primary",
  // Phase 4: rider onboarding
  PENDING: "warning",
  UNDER_REVIEW: "warning",
  APPROVED: "success",
  REJECTED: "danger",
  // Phase 4: rider operational status
  OFFLINE: "neutral",
  BUSY: "warning",
  // Phase 4: offer / document verification
  ACCEPTED: "success",
  EXPIRED: "neutral",
  VERIFIED: "success",
  // Phase 5: payments
  INITIATED: "neutral",
  SUCCEEDED: "success",
  FAILED: "danger",
  PARTIALLY_REFUNDED: "warning",
  REFUNDED: "neutral",
  // Phase 5: refunds
  REQUESTED: "warning",
  PROCESSING: "warning",
  // Phase 5: payouts
  PAID: "success",
  // Phase 7: support tickets / disputes / reports
  OPEN: "warning",
  IN_PROGRESS: "primary",
  WAITING_FOR_CUSTOMER: "warning",
  RESOLVED: "success",
  INVESTIGATING: "warning",
  ACTION_REQUIRED: "danger",
  COMPLETED: "success",
};

function formatStatusLabel(status: string): string {
  const spaced = status.replace(/_/g, " ").toLowerCase();
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

export function StatusBadge({ status }: { status: string }) {
  return <Badge tone={roleTone[status] ?? "neutral"}>{formatStatusLabel(status)}</Badge>;
}
