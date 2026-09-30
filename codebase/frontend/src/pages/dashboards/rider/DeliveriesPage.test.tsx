import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ToastProvider } from "../../../context/ToastContext";
import { logisticsService } from "../../../services/logisticsService";
import type { Delivery, DeliveryOffer } from "../../../types/logistics";
import { DeliveriesPage } from "./DeliveriesPage";

vi.mock("../../../services/logisticsService", () => ({
  logisticsService: {
    getCurrentDelivery: vi.fn(),
    listOffers: vi.fn(),
    acceptOffer: vi.fn(),
    rejectOffer: vi.fn(),
    pickup: vi.fn(),
    startDelivering: vi.fn(),
    complete: vi.fn(),
    postLocation: vi.fn(),
  },
}));

vi.mock("../../../context/AuthContext", () => ({
  useAuth: () => ({
    user: { role: "RIDER", full_name: "Sam Rider" },
    isAuthenticated: true,
    isLoading: false,
    logout: vi.fn(),
  }),
}));

function makeOffer(overrides: Partial<DeliveryOffer> = {}): DeliveryOffer {
  return {
    id: "offer-1",
    delivery_id: "delivery-1",
    status: "OFFERED",
    offered_at: new Date().toISOString(),
    expires_at: new Date(Date.now() + 60_000).toISOString(),
    responded_at: null,
    rejection_reason: null,
    ...overrides,
  };
}

function makeDelivery(overrides: Partial<Delivery> = {}): Delivery {
  return {
    id: "delivery-1",
    order_id: "order-1",
    order_number: "ORD-1001",
    branch_id: "branch-1",
    branch_name: "Downtown Diner",
    rider_id: "rider-1",
    rider_name: "Sam Rider",
    status: "ASSIGNED",
    pickup_latitude: 40.7128,
    pickup_longitude: -74.006,
    destination_latitude: 40.73,
    destination_longitude: -73.99,
    assigned_at: new Date().toISOString(),
    picked_up_at: null,
    delivered_at: null,
    cancelled_at: null,
    cancellation_reason: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides,
  };
}

function renderPage() {
  return render(
    <MemoryRouter>
      <ToastProvider>
        <DeliveriesPage />
      </ToastProvider>
    </MemoryRouter>
  );
}

describe("DeliveriesPage - critical rider delivery flow", () => {
  beforeEach(() => {
    vi.mocked(logisticsService.getCurrentDelivery).mockResolvedValue(null);
    vi.mocked(logisticsService.listOffers).mockResolvedValue([]);
  });

  it("shows a pending offer and accepts it, revealing the active delivery", async () => {
    const user = userEvent.setup();
    vi.mocked(logisticsService.listOffers).mockResolvedValue([makeOffer()]);
    vi.mocked(logisticsService.acceptOffer).mockResolvedValue(makeDelivery());

    renderPage();

    expect(await screen.findByText("You have 1 pending delivery offer.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Accept" }));

    await waitFor(() => expect(logisticsService.acceptOffer).toHaveBeenCalledWith("offer-1"));
    expect(await screen.findByText("Delivery accepted.")).toBeInTheDocument();
    expect(await screen.findByText("ORD-1001")).toBeInTheDocument();
  });

  it("declines an offer and reloads the offer list", async () => {
    const user = userEvent.setup();
    vi.mocked(logisticsService.listOffers).mockResolvedValueOnce([makeOffer()]).mockResolvedValueOnce([]);
    vi.mocked(logisticsService.rejectOffer).mockResolvedValue(undefined);

    renderPage();
    await screen.findByRole("button", { name: "Decline" });
    await user.click(screen.getByRole("button", { name: "Decline" }));

    await waitFor(() => expect(logisticsService.rejectOffer).toHaveBeenCalledWith("offer-1"));
    expect(await screen.findByText("Offer declined.")).toBeInTheDocument();
  });

  it("advances an assigned delivery through pickup", async () => {
    const user = userEvent.setup();
    vi.mocked(logisticsService.getCurrentDelivery).mockResolvedValue(makeDelivery({ status: "ASSIGNED" }));
    vi.mocked(logisticsService.pickup).mockResolvedValue(makeDelivery({ status: "PICKED_UP" }));

    renderPage();

    const pickupButton = await screen.findByRole("button", { name: "Mark picked up" });
    await user.click(pickupButton);

    await waitFor(() => expect(logisticsService.pickup).toHaveBeenCalledWith("delivery-1"));
    expect(await screen.findByText("Marked as picked up.")).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Start delivering" })).toBeInTheDocument();
  });

  it("completing the final leg clears the active delivery and reloads for new offers", async () => {
    const user = userEvent.setup();
    vi.mocked(logisticsService.getCurrentDelivery)
      .mockResolvedValueOnce(makeDelivery({ status: "DELIVERING" }))
      .mockResolvedValueOnce(null);
    vi.mocked(logisticsService.complete).mockResolvedValue(makeDelivery({ status: "DELIVERED" }));

    renderPage();
    const completeButton = await screen.findByRole("button", { name: "Mark delivered" });
    await user.click(completeButton);

    await waitFor(() => expect(logisticsService.complete).toHaveBeenCalledWith("delivery-1"));
    expect(await screen.findByText("Delivery completed.")).toBeInTheDocument();
    expect(await screen.findByText("No delivery offers")).toBeInTheDocument();
  });

  it("shows an error toast when an offer can no longer be accepted", async () => {
    const user = userEvent.setup();
    vi.mocked(logisticsService.listOffers).mockResolvedValue([makeOffer()]);
    vi.mocked(logisticsService.acceptOffer).mockRejectedValueOnce(new Error("expired"));

    renderPage();
    await user.click(await screen.findByRole("button", { name: "Accept" }));

    expect(await screen.findByText("This offer is no longer available.")).toBeInTheDocument();
  });

  it("shows an empty state when there is no active delivery and no offers", async () => {
    renderPage();
    expect(await screen.findByText("No delivery offers")).toBeInTheDocument();
  });
});
