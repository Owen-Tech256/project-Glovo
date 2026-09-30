import { describe, expect, it } from "vitest";
import { isValidEmail, isValidPhone, passwordIssue } from "./validation";

describe("isValidEmail", () => {
  it("accepts well-formed addresses", () => {
    expect(isValidEmail("person@example.com")).toBe(true);
    expect(isValidEmail("first.last+tag@sub.example.co")).toBe(true);
  });

  it("trims surrounding whitespace before checking", () => {
    expect(isValidEmail("  person@example.com  ")).toBe(true);
  });

  it("rejects malformed addresses", () => {
    expect(isValidEmail("not-an-email")).toBe(false);
    expect(isValidEmail("missing-domain@")).toBe(false);
    expect(isValidEmail("@missing-local.com")).toBe(false);
    expect(isValidEmail("has spaces@example.com")).toBe(false);
    expect(isValidEmail("")).toBe(false);
  });
});

describe("isValidPhone", () => {
  it("accepts digits with an optional leading +", () => {
    expect(isValidPhone("+15551234567")).toBe(true);
    expect(isValidPhone("5551234567")).toBe(true);
  });

  it("rejects too-short, too-long or non-numeric values", () => {
    expect(isValidPhone("123")).toBe(false);
    expect(isValidPhone("1".repeat(16))).toBe(false);
    expect(isValidPhone("call-me-maybe")).toBe(false);
    expect(isValidPhone("")).toBe(false);
  });
});

describe("passwordIssue", () => {
  it("returns null for a password meeting all rules", () => {
    expect(passwordIssue("Password1")).toBeNull();
  });

  it("flags passwords shorter than 8 characters", () => {
    expect(passwordIssue("Ab1")).toMatch(/at least 8 characters/i);
  });

  it("flags passwords with no letters", () => {
    expect(passwordIssue("12345678")).toMatch(/at least one letter/i);
  });

  it("flags passwords with no numbers", () => {
    expect(passwordIssue("abcdefgh")).toMatch(/at least one number/i);
  });
});
