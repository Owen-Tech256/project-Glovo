import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Mail } from "lucide-react";
import { AuthLayout } from "../../layouts/AuthLayout";
import { Input } from "../../components/ui/Input";
import { PasswordInput } from "../../components/ui/PasswordInput";
import { Button } from "../../components/ui/Button";
import { Alert } from "../../components/ui/Alert";
import { useAuth, extractApiErrorMessage } from "../../context/AuthContext";
import { dashboardPathFor } from "../../routes/guards";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setServerError(null);
    setIsSubmitting(true);
    try {
      const user = await login({ identifier, password, remember_me: rememberMe });
      navigate(dashboardPathFor(user.role), { replace: true });
    } catch (error) {
      setServerError(extractApiErrorMessage(error, "We couldn't log you in. Please check your details and try again."));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AuthLayout
      panelTitle="One account for your whole delivery experience."
      panelDescription="Whether you're ordering, running a shop, or making deliveries, Routeley keeps your account secure and in one place."
    >
      <h1 className="font-display text-2xl font-semibold text-ink mb-1">Log in</h1>
      <p className="text-ink-soft mb-8">Welcome back — enter your details to continue.</p>

      {serverError && (
        <div className="mb-5">
          <Alert tone="danger">{serverError}</Alert>
        </div>
      )}

      <form onSubmit={handleSubmit} noValidate className="space-y-5">
        <Input
          label="Email or phone"
          type="text"
          icon={<Mail className="h-4 w-4" />}
          autoComplete="username"
          required
          value={identifier}
          onChange={(e) => setIdentifier(e.target.value)}
        />
        <PasswordInput
          label="Password"
          required
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        <div className="flex items-center justify-between">
          <label className="flex items-center gap-2 text-sm text-ink-soft">
            <input
              type="checkbox"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
              className="h-4 w-4 rounded border-line-strong text-primary focus:ring-primary"
            />
            Remember me
          </label>
          <Link to="/forgot-password" className="text-sm font-medium text-primary hover:text-primary-dark">
            Forgot password?
          </Link>
        </div>

        <Button type="submit" fullWidth size="lg" isLoading={isSubmitting}>
          Log in
        </Button>
      </form>

      <p className="mt-8 text-sm text-ink-soft">
        Don&apos;t have an account?{" "}
        <Link to="/register" className="font-medium text-primary hover:text-primary-dark">
          Create one
        </Link>
      </p>
    </AuthLayout>
  );
}
