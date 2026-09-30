import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Skeleton, SkeletonBlock, SkeletonList } from "./Skeleton";

describe("Skeleton", () => {
  it("is decorative and hidden from assistive tech", () => {
    const { container } = render(<Skeleton className="h-4 w-full" />);
    expect(container.firstChild).toHaveAttribute("aria-hidden", "true");
  });
});

describe("SkeletonList", () => {
  it("announces itself as loading content to assistive tech", () => {
    render(<SkeletonList />);
    expect(screen.getByRole("status", { name: "Loading content" })).toBeInTheDocument();
  });

  it("defaults to 5 placeholder rows", () => {
    const { container } = render(<SkeletonList />);
    const status = screen.getByRole("status");
    expect(status.children).toHaveLength(5);
    void container;
  });

  it("renders the requested number of rows", () => {
    render(<SkeletonList rows={3} />);
    expect(screen.getByRole("status").children).toHaveLength(3);
  });
});

describe("SkeletonBlock", () => {
  it("announces itself as loading content to assistive tech", () => {
    render(<SkeletonBlock />);
    expect(screen.getByRole("status", { name: "Loading content" })).toBeInTheDocument();
  });
});
