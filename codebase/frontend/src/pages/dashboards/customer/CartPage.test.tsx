import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ToastProvider } from "../../../context/ToastContext";
import { cartService } from "../../../services/cartService";
import type { Cart } from "../../../types/cart";
import { CartPage } from "./CartPage";

vi.mock("../../../services/cartService", () => ({
  cartService: {
    listActiveCarts: vi.fn(),
    getCartForBranch: vi.fn(),
    updateItemQuantity: vi.fn(),
    removeItem: vi.fn(),
  },
}));

vi.mock("../../../context/AuthContext", () => ({
  useAuth: () => ({
    user: { role: "CUSTOMER", full_name: "Jane Doe" },
    isAuthenticated: true,
    isLoading: false,
    logout: vi.fn(),
  }),
}));

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

function makeCart(overrides: Partial<Cart> = {}): Cart {
  return {
    id: "cart-1",
    branch_id: "branch-1",
    branch_name: "Downtown Diner",
    status: "ACTIVE",
    items: [
      {
        id: "item-1",
        product: { id: "prod-1", name: "Cheeseburger", description: null, price: "9.00" },
        branch_product_id: "bp-1",
        quantity: 2,
        unit_price_snapshot: "9.00",
        current_unit_price: "9.00",
        price_changed: false,
        line_total: "18.00",
        is_available: true,
        created_at: null,
        updated_at: null,
      },
    ],
    subtotal: "18.00",
    item_count: 2,
    has_issues: false,
    issues: [],
    created_at: null,
    updated_at: null,
    ...overrides,
  };
}

function renderCartPage() {
  return render(
    <MemoryRouter>
      <ToastProvider>
        <CartPage />
      </ToastProvider>
    </MemoryRouter>
  );
}

describe("CartPage - critical customer purchase flow", () => {
  beforeEach(() => {
    vi.mocked(cartService.listActiveCarts).mockResolvedValue([makeCart()]);
    vi.mocked(cartService.updateItemQuantity).mockResolvedValue(makeCart());
    vi.mocked(cartService.removeItem).mockResolvedValue(undefined);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("loads and displays the active cart", async () => {
    renderCartPage();
    expect(await screen.findByText("Cheeseburger")).toBeInTheDocument();
    expect(screen.getByText("Downtown Diner")).toBeInTheDocument();
  });

  it("increasing quantity calls updateItemQuantity with quantity + 1", async () => {
    const user = userEvent.setup();
    renderCartPage();
    await screen.findByText("Cheeseburger");

    await user.click(screen.getByLabelText("Increase quantity"));

    await waitFor(() => expect(cartService.updateItemQuantity).toHaveBeenCalledWith("item-1", 3));
  });

  it("decreasing quantity to zero removes the item instead of updating it", async () => {
    const user = userEvent.setup();
    vi.mocked(cartService.listActiveCarts).mockResolvedValue([
      makeCart({
        items: [
          {
            id: "item-1",
            product: { id: "prod-1", name: "Cheeseburger", description: null, price: "9.00" },
            branch_product_id: "bp-1",
            quantity: 1,
            unit_price_snapshot: "9.00",
            current_unit_price: "9.00",
            price_changed: false,
            line_total: "9.00",
            is_available: true,
            created_at: null,
            updated_at: null,
          },
        ],
      }),
    ]);
    renderCartPage();
    await screen.findByText("Cheeseburger");

    await user.click(screen.getByLabelText("Decrease quantity"));

    await waitFor(() => expect(cartService.removeItem).toHaveBeenCalledWith("item-1"));
    expect(cartService.updateItemQuantity).not.toHaveBeenCalled();
  });

  it("the remove button removes the item directly", async () => {
    const user = userEvent.setup();
    renderCartPage();
    await screen.findByText("Cheeseburger");

    await user.click(screen.getByLabelText("Remove item"));

    await waitFor(() => expect(cartService.removeItem).toHaveBeenCalledWith("item-1"));
  });

  it("proceeding to checkout navigates with the branch id when the cart is healthy", async () => {
    const user = userEvent.setup();
    renderCartPage();
    await screen.findByText("Cheeseburger");

    const checkoutButton = screen.getByRole("button", { name: "Proceed to checkout" });
    expect(checkoutButton).toBeEnabled();

    await user.click(checkoutButton);
    expect(mockNavigate).toHaveBeenCalledWith("/customer/dashboard/checkout?branch=branch-1");
  });

  it("disables checkout when the cart has unresolved issues", async () => {
    vi.mocked(cartService.listActiveCarts).mockResolvedValue([
      makeCart({
        has_issues: true,
        issues: [{ cart_item_id: "item-1", product_name: "Cheeseburger", reason: "PRODUCT_UNAVAILABLE" }],
      }),
    ]);
    renderCartPage();
    await screen.findByRole("alert");

    expect(screen.getByRole("button", { name: "Proceed to checkout" })).toBeDisabled();
    expect(screen.getByRole("alert")).toHaveTextContent("is no longer available");
  });

  it("shows an error toast when updating the cart fails", async () => {
    const user = userEvent.setup();
    vi.mocked(cartService.updateItemQuantity).mockRejectedValueOnce(new Error("network error"));
    renderCartPage();
    await screen.findByText("Cheeseburger");

    await user.click(screen.getByLabelText("Increase quantity"));

    expect(await screen.findByText("Could not update your cart.")).toBeInTheDocument();
  });

  it("shows an empty state with no active carts", async () => {
    vi.mocked(cartService.listActiveCarts).mockResolvedValue([]);
    renderCartPage();
    expect(await screen.findByText("Your cart is empty")).toBeInTheDocument();
  });
});
