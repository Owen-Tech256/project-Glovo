import { forwardRef, useId, type SelectHTMLAttributes } from "react";
import { ChevronDown } from "lucide-react";

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
  error?: string;
  hint?: string;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, error, hint, id, className = "", children, ...rest }, ref) => {
    // See Input.tsx for why this doesn't derive the id from the label text.
    const generatedId = useId();
    const inputId = id ?? generatedId;
    const describedBy = error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined;

    return (
      <div className="flex flex-col gap-1.5">
        <label htmlFor={inputId} className="text-sm font-medium text-ink">
          {label}
        </label>
        <div
          className={`relative flex items-center rounded-md border bg-paper-raised px-3 transition-colors ${
            error ? "border-danger" : "border-line-strong focus-within:border-primary"
          }`}
        >
          <select
            ref={ref}
            id={inputId}
            aria-invalid={Boolean(error)}
            aria-describedby={describedBy}
            className={`w-full appearance-none bg-transparent py-2.5 pr-6 text-sm text-ink outline-none ${className}`}
            {...rest}
          >
            {children}
          </select>
          <ChevronDown className="pointer-events-none absolute right-2.5 h-4 w-4 text-ink-soft" aria-hidden="true" />
        </div>
        {error && (
          <p id={`${inputId}-error`} className="text-sm text-danger">
            {error}
          </p>
        )}
        {!error && hint && (
          <p id={`${inputId}-hint`} className="text-sm text-ink-soft">
            {hint}
          </p>
        )}
      </div>
    );
  }
);
Select.displayName = "Select";
