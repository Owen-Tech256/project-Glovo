import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Select } from "./Select";

describe("Select", () => {
  it("associates the label and lets the user choose an option via the keyboard", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <Select label="Role" value="" onChange={onChange}>
        <option value="">All roles</option>
        <option value="CUSTOMER">Customer</option>
        <option value="VENDOR">Vendor</option>
      </Select>
    );

    const select = screen.getByLabelText("Role") as HTMLSelectElement;
    await user.selectOptions(select, "VENDOR");

    expect(onChange).toHaveBeenCalled();
  });

  it("shows a validation error and marks the field invalid", () => {
    render(
      <Select label="Status" value="" onChange={() => {}} error="Choose a status.">
        <option value="">Choose one</option>
      </Select>
    );

    const select = screen.getByLabelText("Status");
    expect(select).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText("Choose a status.")).toBeInTheDocument();
  });
});
