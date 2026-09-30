import type { ReactNode } from "react";

export function EmptyState({
  icon,
  title,
  description,
}: {
  icon: ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-line-strong px-6 py-12 text-center">
      <div className="flex h-11 w-11 items-center justify-center rounded-full bg-ink/[0.04] text-ink-soft">{icon}</div>
      <div className="space-y-1">
        <p className="font-medium text-ink">{title}</p>
        <p className="text-sm text-ink-soft max-w-sm">{description}</p>
      </div>
    </div>
  );
}
