import { forwardRef, useState, type InputHTMLAttributes } from "react";
import { Eye, EyeOff, Lock } from "lucide-react";
import { Input } from "./Input";

interface PasswordInputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
  hint?: string;
}

export const PasswordInput = forwardRef<HTMLInputElement, PasswordInputProps>(
  ({ label, error, hint, ...rest }, ref) => {
    const [visible, setVisible] = useState(false);

    return (
      <Input
        ref={ref}
        label={label}
        error={error}
        hint={hint}
        type={visible ? "text" : "password"}
        icon={<Lock className="h-4 w-4" />}
        autoComplete={rest.autoComplete ?? "current-password"}
        trailing={
          <button
            type="button"
            onClick={() => setVisible((v) => !v)}
            aria-label={visible ? "Hide password" : "Show password"}
            className="text-ink-soft hover:text-ink shrink-0"
          >
            {visible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        }
        {...rest}
      />
    );
  }
);
PasswordInput.displayName = "PasswordInput";
