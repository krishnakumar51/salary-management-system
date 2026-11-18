import { describe, expect, it } from "vitest";

import { buildQuery, resolveApiBase } from "@/services/api";

describe("resolveApiBase", () => {
  it("uses the configured URL and strips a trailing slash", () => {
    expect(resolveApiBase("https://api.example.com/", true)).toBe("https://api.example.com");
    expect(resolveApiBase("http://localhost:8001", false)).toBe("http://localhost:8001");
  });

  it("falls back to localhost only in development", () => {
    expect(resolveApiBase(undefined, false)).toBe("http://localhost:8000");
  });

  it("refuses to guess in a production build", () => {
    expect(resolveApiBase(undefined, true)).toBeNull();
    expect(resolveApiBase("", true)).toBeNull();
  });
});

describe("buildQuery", () => {
  it("omits empty values and encodes the rest", () => {
    expect(buildQuery({ q: "a b", page: 2, empty: "", none: undefined, zero: 0 })).toBe("?q=a+b&page=2&zero=0");
    expect(buildQuery({})).toBe("");
  });
});
