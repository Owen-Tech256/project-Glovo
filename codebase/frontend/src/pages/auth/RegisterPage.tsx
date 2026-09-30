import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { UserRound, Mail, Phone } from "lucide-react";
import { AuthLayout } from "../../layouts/AuthLayout";
import { Input } from "../../components/ui/Input";
import { PasswordInput } from "../../components/ui/PasswordInput";
import { Button } from "../../components/ui/Button";
import { Alert } from "../../components/ui/Alert";
import { useAuth, extractApiErrorMessage } from "../../context/AuthContext";
import { dashboardPathFor } from "../../routes/guards";
import { isValidEmail, isValidPhone, passwordIssue } from "../../utils/validation";
import type { UserRole } from "../../types/auth";

interface RegisterPageProps {
  role: Exclude<UserRole, "ADMIN">;
  heading: string;
  subheading: string;
  panelTitle: string;
  panelDescription: string;
  loginTo?: string;
}

interface FieldErrors {
  full_name?: string;
  email?: string;
  phone?: string;
  password?: string;
  password_confirmation?: string;
}

export function RegisterPage({ role, heading, subheading, panelTitle, panelDescription }: RegisterPageProps) {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirmation, setPasswordConfirmation] = useState("");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const validate = (): boolean => {
    const errors: FieldErrors = {};
    if (fullName.trim().length < 2) errors.full_name = "Enter your full name.";
    if (!isValidEmail(email)) errors.email = "Enter a valid email address.";
    if (!isValidPhone(phone)) errors.phone = "Enter a valid phone number.";
    const pwIssue = passwordIssue(password);
    if (pwIssue) errors.password = pwIssue;
    if (password !== passwordConfirmation) errors.password_confirmation = "Passwords do not match.";
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setServerError(null);
    if (!validate()) return;

    setIsSubmitting(true);
    try {
      const user = await register({
        full_name: fullName.trim(),
        email: email.trim(),
        phone: phone.trim(),
        password,
        password_confirmation: passwordConfirmation,
        role,
      });
      navigate(dashboardPathFor(user.role), { replace: true });
    } catch (error) {
      setServerError(extractApiErrorMessage(error, "We couldn't create your account. Please check your details and try again."));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AuthLayout panelTitle={panelTitle} panelDescription={panelDescription}>
      <h1 className="font-display text-2xl font-semibold text-ink mb-1">{heading}</h1>
      <p className="text-ink-soft mb-8">{subheading}</p>

      {serverError && (
        <div className="mb-5">
          <Alert tone="danger">{serverError}</Alert>
        </div>
      )}

      <form onSubmit={handleSubmit} noValidate className="space-y-5">
        <Input
          label="Full name"
          icon={<UserRound className="h-4 w-4" />}
          autoComplete="name"
          required
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          error={fieldErrors.full_name}
        />
        <Input
          label="Email"
          type="email"
          icon={<Mail className="h-4 w-4" />}
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          error={fieldErrors.email}
        />
        <Input
          label="Phone number"
          type="tel"
          icon={<Phone className="h-4 w-4" />}
          autoComplete="tel"
          placeholder="+15551234567"
          required
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          error={fieldErrors.phone}
        />
        <PasswordInput
          label="Password"
          autoComplete="new-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          error={fieldErrors.password}
          hint={!fieldErrors.password ? "At least 8 characters, with a letter and a number." : undefined}
        />
        <PasswordInput
          label="Confirm password"
          autoComplete="new-password"
          required
          value={passwordConfirmation}
          onChange={(e) => setPasswordConfirmation(e.target.value)}
          error={fieldErrors.password_confirmation}
        />

        <Button type="submit" fullWidth size="lg" isLoading={isSubmitting}>
          Create account
        </Button>
      </form>

      <p className="mt-8 text-sm text-ink-soft">
        Already have an account?{" "}
        <Link to="/login" className="font-medium text-primary hover:text-primary-dark">
          Log in
        </Link>
      </p>
    </AuthLayout>
  );
}
