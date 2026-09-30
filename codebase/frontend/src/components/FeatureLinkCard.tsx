import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { Card, CardBody } from "./ui/Card";

export function FeatureLinkCard({
  icon,
  title,
  description,
  to,
}: {
  icon: ReactNode;
  title: string;
  description: string;
  to: string;
}) {
  return (
    <Link to={to}>
      <Card className="h-full transition-shadow hover:shadow-md">
        <CardBody className="space-y-3">
          <div className="flex items-start justify-between">
            <div className="h-9 w-9 rounded-md bg-primary-soft text-primary flex items-center justify-center">{icon}</div>
            <ArrowRight className="h-4 w-4 text-ink-soft" />
          </div>
          <div>
            <h3 className="font-medium text-ink mb-1">{title}</h3>
            <p className="text-sm text-ink-soft leading-relaxed">{description}</p>
          </div>
        </CardBody>
      </Card>
    </Link>
  );
}
