import type { ReactNode } from "react";
import { Card, CardBody } from "./ui/Card";
import { Badge } from "./ui/Badge";

export function ComingSoonCard({ icon, title, description }: { icon: ReactNode; title: string; description: string }) {
  return (
    <Card>
      <CardBody className="space-y-3">
        <div className="flex items-start justify-between">
          <div className="h-9 w-9 rounded-md bg-ink/[0.05] text-ink-soft flex items-center justify-center">{icon}</div>
          <Badge tone="neutral">Coming soon</Badge>
        </div>
        <div>
          <h3 className="font-medium text-ink mb-1">{title}</h3>
          <p className="text-sm text-ink-soft leading-relaxed">{description}</p>
        </div>
      </CardBody>
    </Card>
  );
}
