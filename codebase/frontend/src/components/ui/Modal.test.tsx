import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { Modal } from "./Modal";

describe("Modal", () => {
  it("renders nothing when closed", () => {
    render(
      <Modal open={false} onClose={() => {}} title="Edit user">
        <p>Body content</p>
      </Modal>
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("renders as an accessible dialog labeled by its title when open", () => {
    render(
      <Modal open onClose={() => {}} title="Edit user">
        <p>Body content</p>
      </Modal>
    );

    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(dialog).toHaveAccessibleName("Edit user");
    expect(screen.getByText("Body content")).toBeInTheDocument();
  });

  it("calls onClose when the close button is activated", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(
      <Modal open onClose={onClose} title="Edit user">
        <p>Body content</p>
      </Modal>
    );

    await user.click(screen.getByRole("button", { name: "Close dialog" }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when the Escape key is pressed", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(
      <Modal open onClose={onClose} title="Edit user">
        <p>Body content</p>
      </Modal>
    );

    await user.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("moves focus into the dialog when it opens", async () => {
    render(
      <Modal open onClose={() => {}} title="Edit user">
        <button>Save</button>
      </Modal>
    );

    // The close button is the first focusable element in the dialog.
    await waitFor(() => expect(screen.getByRole("button", { name: "Close dialog" })).toHaveFocus());
  });

  it("traps Tab focus inside the dialog", async () => {
    const user = userEvent.setup();
    render(
      <Modal open onClose={() => {}} title="Edit user">
        <button>Save</button>
      </Modal>
    );

    const closeButton = screen.getByRole("button", { name: "Close dialog" });
    const saveButton = screen.getByRole("button", { name: "Save" });
    await waitFor(() => expect(closeButton).toHaveFocus());

    // Forward from the last focusable element wraps back to the first.
    saveButton.focus();
    await user.keyboard("{Tab}");
    expect(closeButton).toHaveFocus();

    // Shift+Tab from the first focusable element wraps to the last.
    await user.keyboard("{Shift>}{Tab}{/Shift}");
    expect(saveButton).toHaveFocus();
  });

  it("restores focus to the triggering element when it closes", async () => {
    const user = userEvent.setup();

    function Harness() {
      const [open, setOpen] = useState(false);
      return (
        <>
          <button onClick={() => setOpen(true)}>Open modal</button>
          <Modal open={open} onClose={() => setOpen(false)} title="Edit user">
            <p>Body content</p>
          </Modal>
        </>
      );
    }

    render(<Harness />);
    const trigger = screen.getByRole("button", { name: "Open modal" });
    trigger.focus();
    await user.click(trigger);

    await waitFor(() => expect(screen.getByRole("button", { name: "Close dialog" })).toHaveFocus());
    await user.keyboard("{Escape}");

    await waitFor(() => expect(trigger).toHaveFocus());
  });
});
