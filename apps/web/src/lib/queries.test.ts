import { describe, expect, it } from "vitest";

import { callPollInterval } from "./queries";

// `useCall` drives the call detail page's live progress indicator off its
// polling interval. The create + "Run analysis immediately" flow writes
// `status="uploaded"` first and only then flips to `"processing"`, so a detail
// page whose first fetch lands during the `uploaded` window MUST keep polling —
// otherwise TanStack Query caches `uploaded` and the page never observes
// processing->done without a manual reload (the reported blocker).
describe("callPollInterval", () => {
  it("polls while a freshly-created call is still 'uploaded'", () => {
    expect(callPollInterval("uploaded")).toBeGreaterThan(0);
  });

  it("polls while a call is 'processing'", () => {
    expect(callPollInterval("processing")).toBeGreaterThan(0);
  });

  it("stops polling once the call reaches a terminal status", () => {
    expect(callPollInterval("done")).toBe(false);
    expect(callPollInterval("error")).toBe(false);
  });

  it("does not poll before the first fetch resolves (status undefined)", () => {
    expect(callPollInterval(undefined)).toBe(false);
  });
});
