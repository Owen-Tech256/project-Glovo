import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Badge, StatusBadge } from "./Badge";

describe("Badge", () => {
  it("renders its text content", () => {
    render(<Badge tone="success">Active</Badge>);
    expect(screen.getByText("Active")).toBeInTheDocument();
  });
});

describe("StatusBadge", () => {
  it("formats an ALL_CAPS status into sentence case", () => {
    render(<StatusBadge status="PAYMENT_CONFIRMED" />);
    expect(screen.getByText("Payment confirmed")).toBeInTheDocument();
  });

  it("never relies on color alone - the status text is always present", () => {
    render(<StatusBadge status="DELIVERED" />);
    expect(screen.getByText("Delivered")).toBeInTheDocument();
  });

  it("falls back gracefully for a status not in the known map", () => {
    render(<StatusBadge status="SOME_NEW_STATUS" />);
    expect(screen.getByText("Some new status")).toBeInTheDocument();
  });
});
