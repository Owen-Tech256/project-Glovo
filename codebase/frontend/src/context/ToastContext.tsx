import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { CheckCircle2, AlertTriangle, X } from "lucide-react";

interface Toast {
  id: number;
  message: string;
  tone: "success" | "danger";
}

interface ToastContextValue {
  showSuccess: (message: string) => void;
  showError: (message: string) => void;
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined);

let nextId = 1;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((t) => t.id !== id));
  }, []);

  const push = useCallback(
    (message: string, tone: Toast["tone"]) => {
      const id = nextId++;
      setToasts((current) => [...current, { id, message, tone }]);
      window.setTimeout(() => dismiss(id), 5000);
    },
    [dismiss]
  );

  const value = useMemo<ToastContextValue>(
    () => ({
      showSuccess: (message: string) => push(message, "success"),
      showError: (message: string) => push(message, "danger"),
    }),
    [push]
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 w-full max-w-sm px-4 sm:px-0">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            role="status"
            className={`flex items-start gap-2 rounded-md border px-3.5 py-3 shadow-sm text-sm bg-paper-raised ${
              toast.tone === "success" ? "border-primary/30" : "border-danger/30"
            }`}
          >
            {toast.tone === "success" ? (
              <CheckCircle2 className="h-4 w-4 shrink-0 text-primary" />
            ) : (
              <AlertTriangle className="h-4 w-4 shrink-0 text-danger" />
            )}
            <span className="flex-1 text-ink">{toast.message}</span>
            <button onClick={() => dismiss(toast.id)} aria-label="Dismiss notification" className="text-ink-soft hover:text-ink">
              <X className="h-4 w-4" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within a ToastProvider.");
  return ctx;
}
