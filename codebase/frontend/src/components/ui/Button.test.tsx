import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Button } from "./Button";

describe("Button", () => {
  it("renders its label and responds to clicks", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Save changes</Button>);

    const button = screen.getByRole("button", { name: "Save changes" });
    await user.click(button);

    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("is disabled and unclickable while isLoading", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    render(
      <Button isLoading onClick={onClick}>
        Save changes
      </Button>
    );

    const button = screen.getByRole("button", { name: "Save changes" });
    expect(button).toBeDisabled();

    await user.click(button);
    expect(onClick).not.toHaveBeenCalled();
  });

  it("respects an explicit disabled prop", () => {
    render(<Button disabled>Save changes</Button>);
    expect(screen.getByRole("button", { name: "Save changes" })).toBeDisabled();
  });

  it("does not treat a normal render as disabled", () => {
    render(<Button>Save changes</Button>);
    expect(screen.getByRole("button", { name: "Save changes" })).toBeEnabled();
  });
});
