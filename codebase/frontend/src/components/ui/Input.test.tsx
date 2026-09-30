import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { Input } from "./Input";

describe("Input", () => {
  it("associates the label with the field so it is reachable by accessible name", () => {
    render(<Input label="Email" onChange={() => {}} value="" />);
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
  });

  it("lets the user type and reports the value via onChange", async () => {
    const user = userEvent.setup();
    let value = "";
    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      value = e.target.value;
    };
    const { rerender } = render(<Input label="Email" value={value} onChange={handleChange} />);

    const field = screen.getByLabelText("Email");
    await user.type(field, "a");
    expect(value).toBe("a");
    rerender(<Input label="Email" value={value} onChange={handleChange} />);
  });

  it("shows a validation error, marks the field invalid, and links it via aria-describedby", () => {
    render(<Input label="Email" value="" onChange={() => {}} error="Enter a valid email address." />);

    const field = screen.getByLabelText("Email");
    expect(field).toHaveAttribute("aria-invalid", "true");

    const message = screen.getByText("Enter a valid email address.");
    expect(field.getAttribute("aria-describedby")).toBe(message.id);
  });

  it("shows a hint instead of an error when there is no error", () => {
    render(<Input label="Phone" value="" onChange={() => {}} hint="Include your country code." />);
    expect(screen.getByText("Include your country code.")).toBeInTheDocument();
  });

  it("prefers the error message over the hint when both are supplied", () => {
    render(
      <Input
        label="Phone"
        value=""
        onChange={() => {}}
        hint="Include your country code."
        error="Enter a valid phone number."
      />
    );
    expect(screen.getByText("Enter a valid phone number.")).toBeInTheDocument();
    expect(screen.queryByText("Include your country code.")).not.toBeInTheDocument();
  });

  it("forwards disabled state", () => {
    render(<Input label="Email" value="" onChange={() => {}} disabled />);
    expect(screen.getByLabelText("Email")).toBeDisabled();
  });
});
