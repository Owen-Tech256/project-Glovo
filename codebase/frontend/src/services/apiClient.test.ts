import { AxiosError, AxiosHeaders } from "axios";
import { describe, expect, it } from "vitest";
import { extractApiErrorMessage } from "./apiClient";

function makeAxiosError(status: number, body?: unknown): AxiosError {
  return new AxiosError(
    "Request failed",
    String(status),
    { headers: new AxiosHeaders() },
    {},
    {
      status,
      statusText: String(status),
      headers: {},
      config: { headers: new AxiosHeaders() },
      data: body,
    }
  );
}

describe("extractApiErrorMessage", () => {
  it("surfaces the backend's error.message when present", () => {
    const error = makeAxiosError(422, { error: { message: "Email is already taken." } });
    expect(extractApiErrorMessage(error)).toBe("Email is already taken.");
  });

  it.each([401, 403, 404, 409, 429, 500, 503])(
    "still surfaces error.message for a %i response",
    (status) => {
      const error = makeAxiosError(status, { error: { message: `status ${status}` } });
      expect(extractApiErrorMessage(error)).toBe(`status ${status}`);
    }
  );

  it("falls back to the default message when the body has no error.message", () => {
    const error = makeAxiosError(500, { unexpected: "shape" });
    expect(extractApiErrorMessage(error)).toBe("Something went wrong. Please try again.");
  });

  it("falls back to a caller-supplied message", () => {
    const error = makeAxiosError(400, {});
    expect(extractApiErrorMessage(error, "Could not save changes.")).toBe("Could not save changes.");
  });

  it("falls back to the default message for a non-axios error", () => {
    expect(extractApiErrorMessage(new Error("network down"))).toBe(
      "Something went wrong. Please try again."
    );
  });

  it("falls back to the default message when there is no response at all", () => {
    const error = new AxiosError("Network Error", "ERR_NETWORK", { headers: new AxiosHeaders() });
    expect(extractApiErrorMessage(error)).toBe("Something went wrong. Please try again.");
  });
});
