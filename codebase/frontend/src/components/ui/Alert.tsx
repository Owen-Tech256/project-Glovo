import type { ReactNode } from "react";
import { AlertTriangle, CheckCircle2, Info, TriangleAlert } from "lucide-react";

type Tone = "danger" | "success" | "info" | "warning";

const config: Record<Tone, { icon: ReactNode; classes: string }> = {
  danger: { icon: <AlertTriangle className="h-4 w-4 shrink-0" />, classes: "bg-danger-soft text-danger border-danger/20" },
  success: { icon: <CheckCircle2 className="h-4 w-4 shrink-0" />, classes: "bg-primary-soft text-primary-dark border-primary/20" },
  info: { icon: <Info className="h-4 w-4 shrink-0" />, classes: "bg-ink/[0.04] text-ink-soft border-line" },
  warning: { icon: <TriangleAlert className="h-4 w-4 shrink-0" />, classes: "bg-warning-soft text-warning border-warning/20" },
};

export function Alert({ tone = "info", children }: { tone?: Tone; children: ReactNode }) {
  const { icon, classes } = config[tone];
  return (
    <div role={tone === "danger" || tone === "warning" ? "alert" : "status"} className={`flex items-start gap-2 rounded-md border px-3 py-2.5 text-sm ${classes}`}>
      {icon}
      <div>{children}</div>
    </div>
  );
}
