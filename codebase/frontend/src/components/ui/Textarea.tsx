import { forwardRef, useId, type TextareaHTMLAttributes } from "react";

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label: string;
  error?: string;
  hint?: string;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ label, error, hint, id, className = "", rows = 3, ...rest }, ref) => {
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
          className={`rounded-md border bg-paper-raised px-3 transition-colors ${
            error ? "border-danger" : "border-line-strong focus-within:border-primary"
          }`}
        >
          <textarea
            ref={ref}
            id={inputId}
            rows={rows}
            aria-invalid={Boolean(error)}
            aria-describedby={describedBy}
            className={`w-full bg-transparent py-2.5 text-sm text-ink placeholder:text-ink-soft/60 outline-none resize-y ${className}`}
            {...rest}
          />
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
Textarea.displayName = "Textarea";
