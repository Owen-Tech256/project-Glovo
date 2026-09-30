import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Alert } from "./Alert";

describe("Alert", () => {
  it("renders a danger alert with an assertive alert role", () => {
    render(<Alert tone="danger">Something went wrong.</Alert>);
    expect(screen.getByRole("alert")).toHaveTextContent("Something went wrong.");
  });

  it("renders a warning alert with an assertive alert role", () => {
    render(<Alert tone="warning">Your session will expire soon.</Alert>);
    expect(screen.getByRole("alert")).toHaveTextContent("Your session will expire soon.");
  });

  it("renders a success alert with a polite status role", () => {
    render(<Alert tone="success">Changes saved.</Alert>);
    expect(screen.getByRole("status")).toHaveTextContent("Changes saved.");
  });

  it("renders an info alert with a polite status role", () => {
    render(<Alert tone="info">Delivery usually takes 30-45 minutes.</Alert>);
    expect(screen.getByRole("status")).toHaveTextContent("Delivery usually takes 30-45 minutes.");
  });

  it("defaults to the info tone when none is given", () => {
    render(<Alert>Heads up.</Alert>);
    expect(screen.getByRole("status")).toHaveTextContent("Heads up.");
  });
});
