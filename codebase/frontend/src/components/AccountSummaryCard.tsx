import { Mail, Phone, Calendar } from "lucide-react";
import { Card, CardBody, CardHeader } from "./ui/Card";
import { StatusBadge } from "./ui/Badge";
import type { User } from "../types/auth";

export function AccountSummaryCard({ user }: { user: User }) {
  const memberSince = new Date(user.created_at).toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  return (
    <Card>
      <CardHeader className="flex items-center justify-between">
        <h2 className="font-medium text-ink">Account</h2>
        <StatusBadge status={user.status} />
      </CardHeader>
      <CardBody className="space-y-3">
        <div className="flex items-center gap-2.5 text-sm text-ink-soft">
          <Mail className="h-4 w-4 shrink-0" />
          {user.email}
        </div>
        {user.phone && (
          <div className="flex items-center gap-2.5 text-sm text-ink-soft">
            <Phone className="h-4 w-4 shrink-0" />
            {user.phone}
          </div>
        )}
        <div className="flex items-center gap-2.5 text-sm text-ink-soft">
          <Calendar className="h-4 w-4 shrink-0" />
          Member since {memberSince}
        </div>
      </CardBody>
    </Card>
  );
}
