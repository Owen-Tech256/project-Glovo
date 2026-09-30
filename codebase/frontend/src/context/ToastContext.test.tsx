import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { ToastProvider, useToast } from "./ToastContext";

function Trigger() {
  const { showSuccess, showError } = useToast();
  return (
    <>
      <button onClick={() => showSuccess("Changes saved.")}>trigger success</button>
      <button onClick={() => showError("Could not save changes.")}>trigger error</button>
    </>
  );
}

describe("ToastProvider / useToast", () => {
  it("shows a success toast with a polite status role when triggered", async () => {
    const user = userEvent.setup();
    render(
      <ToastProvider>
        <Trigger />
      </ToastProvider>
    );

    await user.click(screen.getByText("trigger success"));
    expect(await screen.findByRole("status")).toHaveTextContent("Changes saved.");
  });

  it("shows an error toast that can be dismissed manually", async () => {
    const user = userEvent.setup();
    render(
      <ToastProvider>
        <Trigger />
      </ToastProvider>
    );

    await user.click(screen.getByText("trigger error"));
    const toast = await screen.findByText("Could not save changes.");
    expect(toast).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Dismiss notification" }));
    await waitFor(() => expect(screen.queryByText("Could not save changes.")).not.toBeInTheDocument());
  });

  it("throws a clear error when used outside a provider", () => {
    function Bare() {
      useToast();
      return null;
    }
    expect(() => render(<Bare />)).toThrow(/useToast must be used within a ToastProvider/);
  });
});
