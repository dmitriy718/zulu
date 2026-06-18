import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StatusPanel } from "../components/StatusPanel";
import { localPlatformStatus, summarizeStatus } from "../lib/status";

describe("local platform status", () => {
  it("summarizes healthy services deterministically", () => {
    expect(summarizeStatus(localPlatformStatus)).toBe("1/4 services healthy");
  });

  it("renders the live trading disabled status context", () => {
    render(<StatusPanel status={localPlatformStatus} />);

    expect(screen.getByText("Local platform status")).toBeInTheDocument();
    expect(screen.getByText(/live trading is disabled/i)).toBeInTheDocument();
  });
});
