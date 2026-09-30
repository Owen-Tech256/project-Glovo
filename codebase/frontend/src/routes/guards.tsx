import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import type { UserRole } from "../types/auth";
import { Loader2 } from "lucide-react";

const dashboardPathByRole: Record<UserRole, string> = {
  CUSTOMER: "/customer/dashboard",
  VENDOR: "/vendor/dashboard",
  RIDER: "/rider/dashboard",
  ADMIN: "/admin/dashboard",
};

export function dashboardPathFor(role: UserRole): string {
  return dashboardPathByRole[role];
}

export function FullScreenSpinner() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-paper">
      <Loader2 className="h-6 w-6 animate-spin text-primary" aria-label="Loading" />
    </div>
  );
}

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) return <FullScreenSpinner />;
  if (!isAuthenticated) return <Navigate to="/login" state={{ from: location }} replace />;
  return <>{children}</>;
}

export function RoleRoute({ allowed, children }: { allowed: UserRole[]; children: ReactNode }) {
  const { user, isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) return <FullScreenSpinner />;
  if (!isAuthenticated || !user) return <Navigate to="/login" state={{ from: location }} replace />;
  if (!allowed.includes(user.role)) return <Navigate to={dashboardPathFor(user.role)} replace />;
  return <>{children}</>;
}

export function GuestOnlyRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading, user } = useAuth();

  if (isLoading) return <FullScreenSpinner />;
  if (isAuthenticated && user) return <Navigate to={dashboardPathFor(user.role)} replace />;
  return <>{children}</>;
}
