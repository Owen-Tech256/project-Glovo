import type { ReactNode } from "react";
import { X } from "lucide-react";
import { useFocusTrap } from "../../hooks/useFocusTrap";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children: ReactNode;
  size?: "sm" | "md" | "lg";
}

const sizeClasses: Record<NonNullable<ModalProps["size"]>, string> = {
  sm: "max-w-sm",
  md: "max-w-lg",
  lg: "max-w-2xl",
};

export function Modal({ open, onClose, title, description, children, size = "md" }: ModalProps) {
  const dialogRef = useFocusTrap<HTMLDivElement>(open, onClose);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto p-4 py-8 sm:items-center">
      <div className="fixed inset-0 bg-ink/40" onClick={onClose} aria-hidden="true" />
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        className={`relative w-full ${sizeClasses[size]} rounded-lg border border-line bg-paper-raised shadow-xl`}
      >
        <div className="flex items-start justify-between gap-4 border-b border-line px-5 py-4">
          <div>
            <h2 className="font-display text-base font-semibold text-ink">{title}</h2>
            {description && <p className="mt-0.5 text-sm text-ink-soft">{description}</p>}
          </div>
          <button
            onClick={onClose}
            aria-label="Close dialog"
            className="text-ink-soft hover:text-ink shrink-0 rounded-md p-1 hover:bg-ink/[0.04]"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="px-5 py-4">{children}</div>
      </div>
    </div>
  );
}
