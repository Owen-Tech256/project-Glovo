import { forwardRef, useId, type InputHTMLAttributes, type ReactNode } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  icon?: ReactNode;
  error?: string;
  hint?: string;
  trailing?: ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, icon, error, hint, trailing, id, className = "", ...rest }, ref) => {
    // Falls back to a React-generated id rather than deriving one from the
    // label text - two fields with the same label (e.g. a list filter and a
    // modal field both called "Status") would otherwise render duplicate
    // DOM ids, breaking the label association for one of them.
    const generatedId = useId();
    const inputId = id ?? generatedId;
    const describedBy = error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined;

    return (
      <div className="flex flex-col gap-1.5">
        <label htmlFor={inputId} className="text-sm font-medium text-ink">
          {label}
        </label>
        <div
          className={`flex items-center gap-2 rounded-md border bg-paper-raised px-3 transition-colors ${
            error ? "border-danger" : "border-line-strong focus-within:border-primary"
          }`}
        >
          {icon && <span className="text-ink-soft shrink-0" aria-hidden="true">{icon}</span>}
          <input
            ref={ref}
            id={inputId}
            aria-invalid={Boolean(error)}
            aria-describedby={describedBy}
            className={`w-full bg-transparent py-2.5 text-sm text-ink placeholder:text-ink-soft/60 outline-none ${className}`}
            {...rest}
          />
          {trailing}
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
Input.displayName = "Input";
