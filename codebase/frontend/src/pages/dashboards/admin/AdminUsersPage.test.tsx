import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ToastProvider } from "../../../context/ToastContext";
import { adminUsersService, type UserDetail } from "../../../services/adminUsersService";
import type { User } from "../../../types/auth";
import { AdminUsersPage } from "./AdminUsersPage";

vi.mock("../../../services/adminUsersService", () => ({
  adminUsersService: {
    listUsers: vi.fn(),
    getUser: vi.fn(),
    updateStatus: vi.fn(),
  },
}));

vi.mock("../../../context/AuthContext", () => ({
  useAuth: () => ({
    user: { role: "ADMIN", full_name: "Platform Admin" },
    isAuthenticated: true,
    isLoading: false,
    logout: vi.fn(),
  }),
}));

function makeUser(overrides: Partial<User> = {}): User {
  return {
    id: "user-1",
    full_name: "Jane Doe",
    email: "jane@example.com",
    phone: "+15551234567",
    role: "CUSTOMER",
    status: "ACTIVE",
    is_email_verified: true,
    is_phone_verified: true,
    created_at: new Date().toISOString(),
    last_login_at: null,
    ...overrides,
  };
}

function makeUserDetail(overrides: Partial<UserDetail> = {}): UserDetail {
  return { ...makeUser(), ...overrides };
}

function renderPage() {
  return render(
    <MemoryRouter>
      <ToastProvider>
        <AdminUsersPage />
      </ToastProvider>
    </MemoryRouter>
  );
}

describe("AdminUsersPage - critical admin trust & safety flow", () => {
  beforeEach(() => {
    vi.mocked(adminUsersService.listUsers).mockResolvedValue({
      users: [makeUser()],
      pagination: { page: 1, per_page: 20, total: 1, total_pages: 1 },
    });
  });

  it("opens a user's detail and suspends the account with a reason", async () => {
    const user = userEvent.setup();
    vi.mocked(adminUsersService.getUser).mockResolvedValue(makeUserDetail());
    vi.mocked(adminUsersService.updateStatus).mockResolvedValue(makeUser({ status: "SUSPENDED" }));

    renderPage();

    await user.click(await screen.findByText("Jane Doe"));

    const dialog = await screen.findByRole("dialog", { name: "Jane Doe" });
    expect(dialog).toHaveTextContent("jane@example.com");

    await user.selectOptions(within(dialog).getByLabelText("Status"), "SUSPENDED");
    await user.type(within(dialog).getByLabelText("Reason (optional)"), "Repeated policy violations");
    await user.click(within(dialog).getByRole("button", { name: "Save" }));

    await waitFor(() =>
      expect(adminUsersService.updateStatus).toHaveBeenCalledWith(
        "user-1",
        "SUSPENDED",
        "Repeated policy violations"
      )
    );
    expect(await screen.findByText("User status updated.")).toBeInTheDocument();
    // The modal closes and the list reloads after a successful save.
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(adminUsersService.listUsers).toHaveBeenCalledTimes(2);
  });

  it("disables Save until a different status is actually chosen", async () => {
    const user = userEvent.setup();
    vi.mocked(adminUsersService.getUser).mockResolvedValue(makeUserDetail({ status: "ACTIVE" }));

    renderPage();
    await user.click(await screen.findByText("Jane Doe"));
    await screen.findByRole("dialog");

    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
  });

  it("shows an error toast if the status update fails, and keeps the modal open", async () => {
    const user = userEvent.setup();
    vi.mocked(adminUsersService.getUser).mockResolvedValue(makeUserDetail());
    vi.mocked(adminUsersService.updateStatus).mockRejectedValueOnce(new Error("conflict"));

    renderPage();
    await user.click(await screen.findByText("Jane Doe"));
    const dialog = await screen.findByRole("dialog");

    await user.selectOptions(within(dialog).getByLabelText("Status"), "SUSPENDED");
    await user.click(within(dialog).getByRole("button", { name: "Save" }));

    expect(await screen.findByText("Could not update this user's status.")).toBeInTheDocument();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("shows an empty state when no accounts match the filters", async () => {
    vi.mocked(adminUsersService.listUsers).mockResolvedValue({
      users: [],
      pagination: { page: 1, per_page: 20, total: 0, total_pages: 1 },
    });
    renderPage();
    expect(await screen.findByText("No users found")).toBeInTheDocument();
  });
});
