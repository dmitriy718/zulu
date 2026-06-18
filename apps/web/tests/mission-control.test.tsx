import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AutomationGatePanel } from "../components/AutomationGatePanel";
import { DecisionLedger } from "../components/DecisionLedger";
import { MarketWeatherPanel } from "../components/MarketWeatherPanel";
import { SignalCard } from "../components/SignalCard";
import { fixtureMissionControlData } from "../lib/fixtureData";
import { hasProductMode } from "../lib/platform";

describe("mission-control components", () => {
  it("renders signal cards with risk anatomy and no execution language", () => {
    const [signal] = fixtureMissionControlData.clean_signals;

    render(<SignalCard signal={signal} detailed />);

    expect(screen.getByText("MSFT")).toBeInTheDocument();
    expect(screen.getByText("Stop loss")).toBeInTheDocument();
    expect(screen.getByText("Upside Thesis")).toBeInTheDocument();
    expect(screen.getByText("Downside Risk")).toBeInTheDocument();
    expect(screen.getByText(/Data Limitations/i)).toBeInTheDocument();
    expect(screen.queryByText(/guaranteed/i)).not.toBeInTheDocument();
  });

  it("renders automation gates with live disabled by default", () => {
    render(<AutomationGatePanel data={fixtureMissionControlData} />);

    const modeStatus = screen.getByLabelText("Automation mode status");
    expect(within(modeStatus).getByText("Live")).toBeInTheDocument();
    expect(within(modeStatus).getByText("Disabled")).toBeInTheDocument();
    expect(screen.getByText("RiskGate")).toBeInTheDocument();
    expect(screen.getByText(/live trading is disabled/i)).toBeInTheDocument();
  });

  it("renders market weather components and freshness", () => {
    render(<MarketWeatherPanel data={fixtureMissionControlData} />);

    expect(
      screen.getByRole("heading", { name: /balanced risk-on/i }),
    ).toBeInTheDocument();
    expect(screen.getByText("Index trend")).toBeInTheDocument();
    expect(screen.getByText("Liquidity")).toBeInTheDocument();
    expect(screen.getByText(/as of/i)).toBeInTheDocument();
  });

  it("renders decision ledger trace chronologically", () => {
    render(<DecisionLedger entries={fixtureMissionControlData.ledger} />);

    expect(
      screen.getByText(/Clean MSFT signal delivered/i),
    ).toBeInTheDocument();
    expect(screen.getByText("policy")).toBeInTheDocument();
    expect(screen.getByText("risk")).toBeInTheDocument();
    expect(screen.getByText(/broker route blocked/i)).toBeInTheDocument();
  });

  it("gates Automation Station by subscription mode types", () => {
    expect(
      hasProductMode(fixtureMissionControlData.subscription, "signal_station"),
    ).toBe(true);
    expect(
      hasProductMode(
        fixtureMissionControlData.subscription,
        "automation_station",
      ),
    ).toBe(true);
  });
});
