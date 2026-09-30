import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import type { User } from "../types/auth";
import { GuestOnlyRoute, ProtectedRoute, RoleRoute, dashboardPathFor } from "./guards";

const mockUseAuth = vi.fn();
vi.mock("../context/AuthContext", () => ({
  useAuth: () => mockUseAuth(),
}));

function makeUser(role: User["role"]): User {
  return {
    id: "u1",
    full_name: "Test User",
    email: "test@example.com",
    phone: "+15551234567",
    role,
    status: "ACTIVE",
    created_at: new Date().toISOString(),
  } as User;
}

function renderAt(path: string, element: React.ReactElement, extraRoutes: React.ReactElement[] = []) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/protected" element={element} />
        <Route path="/login" element={<p>Login page</p>} />
        <Route path="/customer/dashboard" element={<p>Customer dashboard</p>} />
        <Route path="/vendor/dashboard" element={<p>Vendor dashboard</p>} />
        <Route path="/rider/dashboard" element={<p>Rider dashboard</p>} />
        <Route path="/admin/dashboard" element={<p>Admin dashboard</p>} />
        {extraRoutes}
      </Routes>
    </MemoryRouter>
  );
}

describe("dashboardPathFor", () => {
  it("maps each role to its own dashboard base path", () => {
    expect(dashboardPathFor("CUSTOMER")).toBe("/customer/dashboard");
    expect(dashboardPathFor("VENDOR")).toBe("/vendor/dashboard");
    expect(dashboardPathFor("RIDER")).toBe("/rider/dashboard");
    expect(dashboardPathFor("ADMIN")).toBe("/admin/dashboard");
  });
});

describe("ProtectedRoute", () => {
  it("shows a spinner while auth state is loading", () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false, isLoading: true });
    renderAt(
      "/protected",
      <ProtectedRoute>
        <p>Secret content</p>
      </ProtectedRoute>
    );
    expect(screen.getByLabelText("Loading")).toBeInTheDocument();
    expect(screen.queryByText("Secret content")).not.toBeInTheDocument();
  });

  it("redirects an unauthenticated user to /login", () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false, isLoading: false });
    renderAt(
      "/protected",
      <ProtectedRoute>
        <p>Secret content</p>
      </ProtectedRoute>
    );
    expect(screen.getByText("Login page")).toBeInTheDocument();
    expect(screen.queryByText("Secret content")).not.toBeInTheDocument();
  });

  it("renders the protected content for an authenticated user", () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: true, isLoading: false });
    renderAt(
      "/protected",
      <ProtectedRoute>
        <p>Secret content</p>
      </ProtectedRoute>
    );
    expect(screen.getByText("Secret content")).toBeInTheDocument();
  });
});

describe("RoleRoute", () => {
  it("redirects to /login when not authenticated", () => {
    mockUseAuth.mockReturnValue({ user: null, isAuthenticated: false, isLoading: false });
    renderAt(
      "/protected",
      <RoleRoute allowed={["ADMIN"]}>
        <p>Admin-only content</p>
      </RoleRoute>
    );
    expect(screen.getByText("Login page")).toBeInTheDocument();
  });

  it("redirects a wrong-role user to their own dashboard rather than showing the content", () => {
    const user = makeUser("CUSTOMER");
    mockUseAuth.mockReturnValue({ user, isAuthenticated: true, isLoading: false });
    renderAt(
      "/protected",
      <RoleRoute allowed={["ADMIN"]}>
        <p>Admin-only content</p>
      </RoleRoute>
    );
    expect(screen.getByText("Customer dashboard")).toBeInTheDocument();
    expect(screen.queryByText("Admin-only content")).not.toBeInTheDocument();
  });

  it("renders the content for a user whose role is in the allowed list", () => {
    const user = makeUser("ADMIN");
    mockUseAuth.mockReturnValue({ user, isAuthenticated: true, isLoading: false });
    renderAt(
      "/protected",
      <RoleRoute allowed={["ADMIN"]}>
        <p>Admin-only content</p>
      </RoleRoute>
    );
    expect(screen.getByText("Admin-only content")).toBeInTheDocument();
  });

  it("allows any role included in a multi-role list", () => {
    const user = makeUser("VENDOR");
    mockUseAuth.mockReturnValue({ user, isAuthenticated: true, isLoading: false });
    renderAt(
      "/protected",
      <RoleRoute allowed={["VENDOR", "ADMIN"]}>
        <p>Shared content</p>
      </RoleRoute>
    );
    expect(screen.getByText("Shared content")).toBeInTheDocument();
  });
});

describe("GuestOnlyRoute", () => {
  it("renders guest content (e.g. the login form) for an unauthenticated visitor", () => {
    mockUseAuth.mockReturnValue({ user: null, isAuthenticated: false, isLoading: false });
    renderAt(
      "/protected",
      <GuestOnlyRoute>
        <p>Login form</p>
      </GuestOnlyRoute>
    );
    expect(screen.getByText("Login form")).toBeInTheDocument();
  });

  it("redirects an already-authenticated user away to their dashboard", () => {
    const user = makeUser("RIDER");
    mockUseAuth.mockReturnValue({ user, isAuthenticated: true, isLoading: false });
    renderAt(
      "/protected",
      <GuestOnlyRoute>
        <p>Login form</p>
      </GuestOnlyRoute>
    );
    expect(screen.getByText("Rider dashboard")).toBeInTheDocument();
    expect(screen.queryByText("Login form")).not.toBeInTheDocument();
  });
});
