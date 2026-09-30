import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ToastProvider } from "../../../context/ToastContext";
import { orderService } from "../../../services/orderService";
import { logisticsService } from "../../../services/logisticsService";
import type { Order, OrderStatusHistoryEntry } from "../../../types/order";
import { VendorOrderDetailPage } from "./OrderDetailPage";

vi.mock("../../../services/orderService", () => ({
  orderService: {
    getVendorOrder: vi.fn(),
    getVendorOrderStatusHistory: vi.fn(),
    transitionVendorOrder: vi.fn(),
  },
}));

vi.mock("../../../services/logisticsService", () => ({
  logisticsService: {
    getVendorOrderDelivery: vi.fn(),
  },
}));

vi.mock("../../../context/AuthContext", () => ({
  useAuth: () => ({
    user: { role: "VENDOR", full_name: "Corner Cafe" },
    isAuthenticated: true,
    isLoading: false,
    logout: vi.fn(),
  }),
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return { ...actual, useParams: () => ({ orderId: "order-1" }) };
});

function makeOrder(overrides: Partial<Order> = {}): Order {
  return {
    id: "order-1",
    order_number: "ORD-1001",
    customer_id: "cust-1",
    branch_id: "branch-1",
    branch_name: "Downtown Diner",
    vendor_name: "Downtown Diner",
    status: "PAYMENT_CONFIRMED",
    subtotal: "18.00",
    fees: "2.00",
    discount_total: "0.00",
    total: "20.00",
    cancelled_at: null,
    cancellation_reason: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    items: [{ id: "item-1", product_name: "Cheeseburger", sku: null, unit_price: "9.00", quantity: 2, line_total: "18.00" }],
    ...overrides,
  };
}

const emptyHistory: OrderStatusHistoryEntry[] = [];

function renderPage() {
  return render(
    <MemoryRouter>
      <ToastProvider>
        <VendorOrderDetailPage />
      </ToastProvider>
    </MemoryRouter>
  );
}

describe("VendorOrderDetailPage - critical vendor order-processing flow", () => {
  beforeEach(() => {
    vi.mocked(logisticsService.getVendorOrderDelivery).mockRejectedValue(new Error("no delivery yet"));
    vi.mocked(orderService.getVendorOrderStatusHistory).mockResolvedValue(emptyHistory);
  });

  it("shows an 'Accept order' action for a freshly paid order, and advances it on click", async () => {
    const user = userEvent.setup();
    vi.mocked(orderService.getVendorOrder).mockResolvedValue(makeOrder());
    vi.mocked(orderService.transitionVendorOrder).mockResolvedValue(makeOrder({ status: "VENDOR_ACCEPTED" }));

    renderPage();

    const acceptButton = await screen.findByRole("button", { name: "Accept order" });
    await user.click(acceptButton);

    await waitFor(() =>
      expect(orderService.transitionVendorOrder).toHaveBeenCalledWith("order-1", "VENDOR_ACCEPTED")
    );
    expect(await screen.findByText("Order updated.")).toBeInTheDocument();
    // The page reloads the order after a successful transition.
    expect(orderService.getVendorOrder).toHaveBeenCalledTimes(2);
  });

  it("labels the action correctly at each stage of the prep pipeline", async () => {
    vi.mocked(orderService.getVendorOrder).mockResolvedValue(makeOrder({ status: "VENDOR_ACCEPTED" }));
    renderPage();
    expect(await screen.findByRole("button", { name: "Start preparing" })).toBeInTheDocument();
  });

  it("shows no advance action once the order has no next status (e.g. READY)", async () => {
    vi.mocked(orderService.getVendorOrder).mockResolvedValue(makeOrder({ status: "READY" }));
    renderPage();
    await screen.findByText("ORD-1001");
    expect(screen.queryByRole("button", { name: /accept order|start preparing|mark ready/i })).not.toBeInTheDocument();
  });

  it("shows an error toast and does not advance the order when the transition fails", async () => {
    const user = userEvent.setup();
    vi.mocked(orderService.getVendorOrder).mockResolvedValue(makeOrder());
    vi.mocked(orderService.transitionVendorOrder).mockRejectedValueOnce(new Error("conflict"));

    renderPage();
    const acceptButton = await screen.findByRole("button", { name: "Accept order" });
    await user.click(acceptButton);

    expect(await screen.findByText("Could not update this order.")).toBeInTheDocument();
  });

  it("shows an empty state when the order cannot be found", async () => {
    vi.mocked(orderService.getVendorOrder).mockRejectedValue(new Error("not found"));
    renderPage();
    expect(await screen.findByText("Order not found")).toBeInTheDocument();
  });
});
