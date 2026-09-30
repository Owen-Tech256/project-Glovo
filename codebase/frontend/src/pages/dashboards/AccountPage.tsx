import { useState, type FormEvent } from "react";
import { DashboardLayout } from "../../layouts/DashboardLayout";
import { Card, CardBody, CardHeader } from "../../components/ui/Card";
import { Input } from "../../components/ui/Input";
import { Button } from "../../components/ui/Button";
import { StatusBadge } from "../../components/ui/Badge";
import { useAuth, extractApiErrorMessage } from "../../context/AuthContext";
import { useToast } from "../../context/ToastContext";

export function AccountPage() {
  const { user, updateProfile } = useAuth();
  const { showSuccess, showError } = useToast();
  const [fullName, setFullName] = useState(user?.full_name ?? "");
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!user) return null;

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (fullName.trim().length < 2) {
      showError("Enter your full name.");
      return;
    }
    setIsSubmitting(true);
    try {
      await updateProfile({ full_name: fullName.trim() });
      showSuccess("Profile updated.");
    } catch (error) {
      showError(extractApiErrorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="max-w-xl space-y-6">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink">My account</h1>
          <p className="text-ink-soft mt-1">Manage your profile details.</p>
        </div>

        <Card>
          <CardHeader className="flex items-center justify-between">
            <h2 className="font-medium text-ink">Profile</h2>
            <StatusBadge status={user.status} />
          </CardHeader>
          <CardBody>
            <form onSubmit={handleSubmit} className="space-y-5">
              <Input label="Full name" value={fullName} onChange={(e) => setFullName(e.target.value)} required />
              <Input label="Email" value={user.email} disabled hint="Email changes aren't available yet." />
              <Input label="Phone" value={user.phone ?? ""} disabled hint="Phone changes aren't available yet." />
              <Button type="submit" isLoading={isSubmitting}>
                Save changes
              </Button>
            </form>
          </CardBody>
        </Card>
      </div>
    </DashboardLayout>
  );
}
