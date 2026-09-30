import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { DashboardLayout } from "./DashboardLayout";

vi.mock("../services/notificationService", () => ({
  notificationService: {
    list: vi.fn().mockResolvedValue({ notifications: [], unread_count: 0 }),
    markRead: vi.fn(),
    markAllRead: vi.fn(),
  },
}));

vi.mock("../context/AuthContext", () => ({
  useAuth: () => ({
    user: { role: "CUSTOMER", full_name: "Jane Doe" },
    isAuthenticated: true,
    isLoading: false,
    logout: vi.fn(),
  }),
}));

vi.mock("../context/ToastContext", () => ({
  useToast: () => ({ showSuccess: vi.fn(), showError: vi.fn() }),
}));

function renderLayout() {
  return render(
    <MemoryRouter>
      <DashboardLayout>
        <p>Page content</p>
      </DashboardLayout>
    </MemoryRouter>
  );
}

describe("DashboardLayout mobile nav - keyboard flow", () => {
  it("opens the drawer and moves focus into it", async () => {
    const user = userEvent.setup();
    renderLayout();

    const openButton = screen.getByRole("button", { name: "Open menu" });
    await user.click(openButton);

    await waitFor(() => expect(screen.getByRole("button", { name: "Close menu" })).toHaveFocus());
  });

  it("closes on Escape and returns focus to the button that opened it", async () => {
    const user = userEvent.setup();
    renderLayout();

    const openButton = screen.getByRole("button", { name: "Open menu" });
    await user.click(openButton);
    await waitFor(() => expect(screen.getByRole("button", { name: "Close menu" })).toHaveFocus());

    await user.keyboard("{Escape}");

    expect(screen.queryByRole("button", { name: "Close menu" })).not.toBeInTheDocument();
    await waitFor(() => expect(openButton).toHaveFocus());
  });

  it("closes when a nav link inside the drawer is activated", async () => {
    const user = userEvent.setup();
    renderLayout();

    await user.click(screen.getByRole("button", { name: "Open menu" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Close menu" })).toHaveFocus());

    // There are two "Browse vendors" links (desktop sidebar + mobile drawer) -
    // the drawer one is the last in DOM order.
    const links = screen.getAllByRole("link", { name: "Browse vendors" });
    await user.click(links[links.length - 1]);

    expect(screen.queryByRole("button", { name: "Close menu" })).not.toBeInTheDocument();
  });
});
