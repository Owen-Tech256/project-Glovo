import { useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { CheckCircle2 } from "lucide-react";
import { AuthLayout } from "../../layouts/AuthLayout";
import { PasswordInput } from "../../components/ui/PasswordInput";
import { Button } from "../../components/ui/Button";
import { Alert } from "../../components/ui/Alert";
import { authService } from "../../services/authService";
import { extractApiErrorMessage } from "../../services/apiClient";
import { passwordIssue } from "../../utils/validation";

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const navigate = useNavigate();

  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setServerError(null);

    const issue = passwordIssue(password);
    if (issue) {
      setFieldError(issue);
      return;
    }
    if (password !== confirmation) {
      setFieldError("Passwords do not match.");
      return;
    }
    setFieldError(null);

    setIsSubmitting(true);
    try {
      await authService.resetPassword(token, password, confirmation);
      setDone(true);
    } catch (error) {
      setServerError(extractApiErrorMessage(error, "This reset link is invalid or has expired."));
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!token) {
    return (
      <AuthLayout panelTitle="Regain access, securely." panelDescription="Reset links expire after 30 minutes for your security.">
        <Alert tone="danger">This password reset link is missing its token. Please request a new one.</Alert>
        <Link to="/forgot-password" className="inline-block mt-5 font-medium text-primary hover:text-primary-dark">
          Request a new reset link
        </Link>
      </AuthLayout>
    );
  }

  if (done) {
    return (
      <AuthLayout panelTitle="Regain access, securely." panelDescription="Reset links expire after 30 minutes for your security.">
        <div className="h-11 w-11 rounded-full bg-primary-soft text-primary-dark flex items-center justify-center mb-5">
          <CheckCircle2 className="h-5 w-5" />
        </div>
        <h1 className="font-display text-2xl font-semibold text-ink mb-2">Password reset</h1>
        <p className="text-ink-soft mb-8">Your password has been updated. Please log in with your new password.</p>
        <Button size="lg" onClick={() => navigate("/login")}>
          Go to log in
        </Button>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout panelTitle="Regain access, securely." panelDescription="Reset links expire after 30 minutes for your security.">
      <h1 className="font-display text-2xl font-semibold text-ink mb-1">Set a new password</h1>
      <p className="text-ink-soft mb-8">Choose a new password for your account.</p>

      {serverError && (
        <div className="mb-5">
          <Alert tone="danger">{serverError}</Alert>
        </div>
      )}

      <form onSubmit={handleSubmit} noValidate className="space-y-5">
        <PasswordInput
          label="New password"
          autoComplete="new-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          error={fieldError ?? undefined}
          hint={!fieldError ? "At least 8 characters, with a letter and a number." : undefined}
        />
        <PasswordInput
          label="Confirm new password"
          autoComplete="new-password"
          required
          value={confirmation}
          onChange={(e) => setConfirmation(e.target.value)}
        />
        <Button type="submit" fullWidth size="lg" isLoading={isSubmitting}>
          Reset password
        </Button>
      </form>
    </AuthLayout>
  );
}
