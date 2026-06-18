import Link from "next/link";
import {
  Activity,
  BadgeCheck,
  BookOpenCheck,
  BrainCircuit,
  CloudSun,
  Gauge,
  Landmark,
  ListChecks,
  Radar,
  RadioTower,
  Settings,
  ShieldCheck,
  Siren,
  SlidersHorizontal,
  Waves,
  Zap,
} from "lucide-react";

import type { MissionControlData } from "../lib/platform";
import { freshnessLabel } from "../lib/platform";

const navItems = [
  ["Command Center", "/", Radar],
  ["Signal Station", "/signal-station", RadioTower],
  ["Automation Station", "/automation-station", Zap],
  ["Market Weather", "/market-weather", CloudSun],
  ["Decision Ledger", "/decision-ledger", ListChecks],
  ["Positions & Orders", "/positions-orders", Landmark],
  ["Learning Lab", "/learning-lab", BookOpenCheck],
  ["Model Health", "/model-health", BrainCircuit],
  ["Incidents & Controls", "/incidents-controls", Siren],
  ["Settings", "/settings", Settings],
] as const;

export function AppShell({
  data,
  active,
  children,
}: Readonly<{
  data: MissionControlData;
  active: string;
  children: React.ReactNode;
}>) {
  const healthySystems = data.pipeline.filter(
    (stage) => stage.status === "ok",
  ).length;

  return (
    <div className="mission-shell">
      <div className="ambient-field" aria-hidden="true">
        <span className="ambient-orbit ambient-orbit-one" />
        <span className="ambient-orbit ambient-orbit-two" />
        <span className="ambient-scanline" />
      </div>

      <aside className="mission-sidebar" aria-label="Zulu primary navigation">
        <Link
          href="/"
          className="brand-lockup"
          aria-label="Zulu Command Center"
        >
          <span className="brand-mark">
            <Waves aria-hidden="true" size={24} strokeWidth={2.4} />
          </span>
          <span>
            <strong>Zulu</strong>
            <small>Command Center</small>
          </span>
        </Link>

        <nav className="primary-nav">
          {navItems.map(([label, href, Icon]) => (
            <Link
              key={href}
              href={href}
              aria-current={active === label ? "page" : undefined}
            >
              <Icon aria-hidden="true" size={17} strokeWidth={2.2} />
              {label}
            </Link>
          ))}
        </nav>

        <section className="sidebar-disclosure" aria-label="Risk disclosure">
          <ShieldCheck aria-hidden="true" size={18} strokeWidth={2.2} />
          <strong>Risk visible</strong>
          <span>
            Stocks/options signals are informational. Automation is gated.
          </span>
        </section>
      </aside>

      <div className="workspace">
        <header className="workspace-header">
          <div>
            <p className="eyebrow">Tenant scoped</p>
            <h1>{active}</h1>
          </div>
          <div className="header-status" aria-label="Current platform state">
            <span>
              <Activity aria-hidden="true" size={15} />
              {healthySystems}/{data.pipeline.length} systems
            </span>
            <span className="data-mode">{data.data_mode} mode</span>
            <span>{data.session.role}</span>
            <span>{data.subscription.plan_code}</span>
            <span aria-label="Live trading status">
              live trading disabled by default
            </span>
            <span>{freshnessLabel(data.market_weather.as_of)}</span>
          </div>
        </header>

        <main id="main-content" className="workspace-main">
          {children}
        </main>
      </div>

      <aside className="floating-command-modal" aria-label="Execution guard">
        <div>
          <p className="eyebrow">Gate console</p>
          <strong>Execution locked</strong>
          <span>{data.automation.environment} environment</span>
        </div>
        <div className="modal-meter" aria-hidden="true">
          <span />
        </div>
        <ul>
          <li>
            <BadgeCheck aria-hidden="true" size={15} />
            PolicyGate required
          </li>
          <li>
            <Gauge aria-hidden="true" size={15} />
            RiskGate required
          </li>
          <li>
            <ShieldCheck aria-hidden="true" size={15} />
            Live disabled
          </li>
        </ul>
        <button type="button" aria-label="View automation gate details">
          <SlidersHorizontal aria-hidden="true" size={17} />
          Gate details
        </button>
      </aside>
    </div>
  );
}
