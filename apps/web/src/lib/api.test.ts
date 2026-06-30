import { describe, expect, it } from "vitest";

import { figureUrl } from "./api";

describe("figureUrl", () => {
  it("builds the figure endpoint from a report-relative path", () => {
    expect(figureUrl("abc", "figures/abc__residuals_vs_fitted.png")).toBe(
      "/runs/abc/figures/abc__residuals_vs_fitted.png",
    );
  });

  it("tolerates a bare filename with no directory", () => {
    expect(figureUrl("abc", "plot.png")).toBe("/runs/abc/figures/plot.png");
  });

  it("encodes the job id", () => {
    expect(figureUrl("a/b", "x.png")).toBe("/runs/a%2Fb/figures/x.png");
  });
});
