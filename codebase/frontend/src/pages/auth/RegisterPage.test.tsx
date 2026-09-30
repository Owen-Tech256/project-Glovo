import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { RegisterPage } from "./RegisterPage";

const mockRegister = vi.fn();
vi.mock("../../context/AuthContext", () => ({
  useAuth: () => ({ register: mockRegister }),
  extractApiErrorMessage: (_err: unknown, fallback: string) => fallback,
}));

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

function renderPage() {
  return render(
    <MemoryRouter>
      <RegisterPage
        role="CUSTOMER"
        heading="Create your account"
        subheading="Start ordering in minutes."
        panelTitle="Panel title"
        panelDescription="Panel description"
      />
    </MemoryRouter>
  );
}

describe("RegisterPage validation", () => {
  it("blocks submission and shows field errors when the form is empty", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole("button", { name: "Create account" }));

    expect(await screen.findByText("Enter your full name.")).toBeInTheDocument();
    expect(screen.getByText("Enter a valid email address.")).toBeInTheDocument();
    expect(screen.getByText("Enter a valid phone number.")).toBeInTheDocument();
    expect(screen.getByText(/at least 8 characters/i)).toBeInTheDocument();
    expect(mockRegister).not.toHaveBeenCalled();
  });

  it("flags a password/confirmation mismatch without touching other valid fields", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText("Full name"), "Jane Doe");
    await user.type(screen.getByLabelText("Email"), "jane@example.com");
    await user.type(screen.getByLabelText("Phone number"), "+15551234567");
    await user.type(screen.getByLabelText("Password"), "Password1");
    await user.type(screen.getByLabelText("Confirm password"), "Password2");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    expect(await screen.findByText("Passwords do not match.")).toBeInTheDocument();
    expect(screen.queryByText("Enter your full name.")).not.toBeInTheDocument();
    expect(mockRegister).not.toHaveBeenCalled();
  });

  it("submits the trimmed, validated payload and navigates on success", async () => {
    const user = userEvent.setup();
    mockRegister.mockResolvedValueOnce({ role: "CUSTOMER" });
    renderPage();

    await user.type(screen.getByLabelText("Full name"), "  Jane Doe  ");
    await user.type(screen.getByLabelText("Email"), "jane@example.com");
    await user.type(screen.getByLabelText("Phone number"), "+15551234567");
    await user.type(screen.getByLabelText("Password"), "Password1");
    await user.type(screen.getByLabelText("Confirm password"), "Password1");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    await vi.waitFor(() => expect(mockRegister).toHaveBeenCalledTimes(1));
    expect(mockRegister).toHaveBeenCalledWith({
      full_name: "Jane Doe",
      email: "jane@example.com",
      phone: "+15551234567",
      password: "Password1",
      password_confirmation: "Password1",
      role: "CUSTOMER",
    });
    expect(mockNavigate).toHaveBeenCalledWith("/customer/dashboard", { replace: true });
  });

  it("shows a server error message and does not navigate when registration fails", async () => {
    const user = userEvent.setup();
    mockRegister.mockRejectedValueOnce(new Error("email already taken"));
    renderPage();

    await user.type(screen.getByLabelText("Full name"), "Jane Doe");
    await user.type(screen.getByLabelText("Email"), "jane@example.com");
    await user.type(screen.getByLabelText("Phone number"), "+15551234567");
    await user.type(screen.getByLabelText("Password"), "Password1");
    await user.type(screen.getByLabelText("Confirm password"), "Password1");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    expect(
      await screen.findByText("We couldn't create your account. Please check your details and try again.")
    ).toBeInTheDocument();
    expect(mockNavigate).not.toHaveBeenCalled();
  });
});
