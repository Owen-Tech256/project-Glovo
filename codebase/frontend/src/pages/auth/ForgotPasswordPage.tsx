import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { Mail, ArrowLeft } from "lucide-react";
import { AuthLayout } from "../../layouts/AuthLayout";
import { Input } from "../../components/ui/Input";
import { Button } from "../../components/ui/Button";
import { Alert } from "../../components/ui/Alert";
import { authService } from "../../services/authService";
import { extractApiErrorMessage } from "../../services/apiClient";

export function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  // Surfaced only because Phase 1 has no email provider wired up yet (the
  // API only returns this in DEBUG/TESTING mode) - lets you exercise the
  // full reset flow locally without a mail server.
  const [devToken, setDevToken] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setServerError(null);
    setIsSubmitting(true);
    try {
      const result = await authService.forgotPassword(email.trim());
      setSubmitted(true);
      setDevToken(result.debug_reset_token ?? null);
    } catch (error) {
      setServerError(extractApiErrorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AuthLayout
      panelTitle="Regain access, securely."
      panelDescription="We'll never confirm whether an email is registered — if it is, a reset link is on its way."
    >
      <Link to="/login" className="inline-flex items-center gap-1.5 text-sm font-medium text-ink-soft hover:text-ink mb-8">
        <ArrowLeft className="h-4 w-4" />
        Back to log in
      </Link>

      <h1 className="font-display text-2xl font-semibold text-ink mb-1">Reset your password</h1>
      <p className="text-ink-soft mb-8">Enter your email and we'll send you a reset link.</p>

      {serverError && (
        <div className="mb-5">
          <Alert tone="danger">{serverError}</Alert>
        </div>
      )}

      {submitted ? (
        <div className="space-y-4">
          <Alert tone="success">
            If an account with that email exists, a password reset link has been sent.
          </Alert>
          {devToken && (
            <div className="rounded-md border border-line bg-ink/[0.03] p-4 text-sm">
              <p className="text-ink-soft mb-2">Local development only — no email provider is configured yet:</p>
              <Link to={`/reset-password?token=${devToken}`} className="font-medium text-primary hover:text-primary-dark break-all">
                Continue to reset password
              </Link>
            </div>
          )}
        </div>
      ) : (
        <form onSubmit={handleSubmit} noValidate className="space-y-5">
          <Input
            label="Email"
            type="email"
            icon={<Mail className="h-4 w-4" />}
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <Button type="submit" fullWidth size="lg" isLoading={isSubmitting}>
            Send reset link
          </Button>
        </form>
      )}
    </AuthLayout>
  );
}
