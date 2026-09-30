import type { ReactNode } from "react";
import { DashboardLayout } from "../../layouts/DashboardLayout";
import { EmptyState } from "../../components/ui/EmptyState";

export function FutureFeaturePage({ icon, title, description }: { icon: ReactNode; title: string; description: string }) {
  return (
    <DashboardLayout>
      <div className="max-w-2xl">
        <h1 className="font-display text-2xl font-semibold text-ink mb-1">{title}</h1>
        <p className="text-ink-soft mb-8">{description}</p>
        <EmptyState
          icon={icon}
          title="Not built yet"
          description="This section is part of a later phase of the marketplace. Your account is ready for when it launches."
        />
      </div>
    </DashboardLayout>
  );
}
