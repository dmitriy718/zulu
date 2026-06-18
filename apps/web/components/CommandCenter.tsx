import {
  Activity,
  ArrowUpRight,
  CloudSun,
  Gauge,
  RadioTower,
  ShieldAlert,
} from "lucide-react";

import type { MissionControlData } from "../lib/platform";
import { formatMoney, formatPercent, freshnessLabel } from "../lib/platform";
import { AutomationGatePanel } from "./AutomationGatePanel";
import { DecisionLedger } from "./DecisionLedger";
import { MarketWeatherPanel } from "./MarketWeatherPanel";
import { SignalCard } from "./SignalCard";
import { SectionHeader, StatusBadge } from "./UI";

export function CommandCenter({
  data,
}: Readonly<{ data: MissionControlData }>) {
  const openOrders = data.order_lifecycle_events.filter(
    (event) => event.status !== "filled" && event.status !== "cancelled",
  );
  return (
    <div className="page-stack">
      <section className="command-hero" aria-label="Today at a glance">
        <div className="hero-copy">
          <p className="eyebrow">Trading mission-control</p>
          <h2>Clean signals, visible uncertainty, and gated automation.</h2>
          <p>
            Today’s view is scoped to {data.tenant.display_name}. Live trading
            is disabled by default; broker-bound work still requires PolicyGate,
            RiskGate, idempotency, and audit context.
          </p>
          <div className="hero-actions" aria-label="Primary command actions">
            <a href="/signal-station">
              <RadioTower aria-hidden="true" size={18} />
              Signal queue
            </a>
            <a href="/automation-station">
              <ShieldAlert aria-hidden="true" size={18} />
              Gate review
            </a>
          </div>
        </div>
        <dl className="hero-metrics">
          <div>
            <dt>
              <CloudSun aria-hidden="true" size={15} />
              Weather
            </dt>
            <dd>{data.market_weather.regime}</dd>
          </div>
          <div>
            <dt>
              <Activity aria-hidden="true" size={15} />
              Headline pressure
            </dt>
            <dd>{data.headline_pressure.level}</dd>
          </div>
          <div>
            <dt>
              <ShieldAlert aria-hidden="true" size={15} />
              Live mode
            </dt>
            <dd>{data.automation.live_enabled ? "Enabled" : "Disabled"}</dd>
          </div>
          <div>
            <dt>
              <Gauge aria-hidden="true" size={15} />
              Risk/trade
            </dt>
            <dd>{formatPercent(data.risk_envelope.max_risk_per_trade)}</dd>
          </div>
        </dl>
      </section>

      <section className="status-matrix" aria-label="Platform status">
        {data.pipeline.map((stage) => (
          <article key={stage.stage}>
            <StatusBadge status={stage.status}>{stage.status}</StatusBadge>
            <h3>
              {stage.stage}
              <ArrowUpRight aria-hidden="true" size={17} />
            </h3>
            <p>{stage.detail}</p>
          </article>
        ))}
      </section>

      <div className="dashboard-grid">
        <MarketWeatherPanel data={data} />
        <AutomationGatePanel data={data} />
      </div>

      <section>
        <SectionHeader
          eyebrow="Recent clean signals"
          title="Signal Station queue"
          description="Each accepted signal has a stop, entry trigger, TP ladder, and decision trace."
        />
        <div className="signal-list">
          {data.clean_signals.map((signal) => (
            <SignalCard key={signal.signal_id} signal={signal} />
          ))}
        </div>
      </section>

      <section className="dashboard-grid">
        <div>
          <SectionHeader
            eyebrow="Open positions/orders"
            title="Paper lifecycle"
          />
          <div
            className="table-panel"
            role="table"
            aria-label="Open positions and orders"
          >
            {data.positions.map((position) => (
              <div role="row" key={position.position_snapshot_id}>
                <span role="cell">{position.ticker}</span>
                <span role="cell">{position.asset_type}</span>
                <span role="cell">{position.quantity}</span>
                <span role="cell">{formatMoney(position.market_value)}</span>
                <span role="cell">{freshnessLabel(position.as_of)}</span>
              </div>
            ))}
            {openOrders.map((event) => (
              <div role="row" key={event.order_lifecycle_event_id}>
                <span role="cell">Order</span>
                <span role="cell">{event.status}</span>
                <span role="cell">{event.broker_order_request_id}</span>
                <span role="cell">pending</span>
                <span role="cell">{freshnessLabel(event.occurred_at)}</span>
              </div>
            ))}
          </div>
        </div>
        <div>
          <SectionHeader eyebrow="Decision ledger" title="Recent trace" />
          <DecisionLedger entries={data.ledger.slice(0, 3)} />
        </div>
      </section>
    </div>
  );
}
