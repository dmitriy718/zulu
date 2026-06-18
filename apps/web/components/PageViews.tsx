import type { MissionControlData } from "../lib/platform";
import { formatMoney, freshnessLabel } from "../lib/platform";
import { AutomationGatePanel } from "./AutomationGatePanel";
import { MarketWeatherPanel } from "./MarketWeatherPanel";
import { SignalCard } from "./SignalCard";
import { EmptyState, SectionHeader, StatusBadge } from "./UI";

export function SignalStationView({
  data,
}: Readonly<{ data: MissionControlData }>) {
  return (
    <div className="page-stack">
      <SectionHeader
        eyebrow="Signal Station"
        title="Clean signal anatomy"
        description="Review signals with explicit entry, stop, thesis, limitations, and durable decision trace."
      />
      <div className="signal-list">
        {data.clean_signals.map((signal) => (
          <SignalCard key={signal.signal_id} signal={signal} detailed />
        ))}
      </div>
      <section className="ack-panel">
        <h2>User acknowledgment</h2>
        <p>
          Acknowledgment records review only. It does not authorize broker
          execution or bypass PolicyGate and RiskGate.
        </p>
        <button type="button" aria-label="Acknowledge selected signal">
          Acknowledge review
        </button>
      </section>
    </div>
  );
}

export function AutomationStationView({
  data,
}: Readonly<{ data: MissionControlData }>) {
  return (
    <div className="page-stack">
      <AutomationGatePanel data={data} />
      <section className="dashboard-grid">
        <div>
          <SectionHeader eyebrow="Broker" title="Connection status" />
          <dl className="fact-list">
            <div>
              <dt>Broker</dt>
              <dd>{data.broker.broker_name}</dd>
            </div>
            <div>
              <dt>Environment</dt>
              <dd>{data.broker.environment}</dd>
            </div>
            <div>
              <dt>Credential configured</dt>
              <dd>{data.broker.credential_configured ? "yes" : "no"}</dd>
            </div>
          </dl>
        </div>
        <div>
          <SectionHeader
            eyebrow="Blocked signals"
            title="Why routing stopped"
          />
          {data.risk_decisions.map((decision) => (
            <article className="reason-row" key={decision.risk_decision_id}>
              <StatusBadge status="blocked">blocked</StatusBadge>
              <div>
                <h3>{decision.signal_id}</h3>
                <p>{decision.reason}</p>
              </div>
            </article>
          ))}
        </div>
      </section>
      <section>
        <SectionHeader eyebrow="Order lifecycle" title="Paper timeline" />
        <div className="timeline">
          {data.order_lifecycle_events.map((event) => (
            <article key={event.order_lifecycle_event_id}>
              <span>{event.status}</span>
              <h3>{event.broker_order_request_id}</h3>
              <p>{freshnessLabel(event.occurred_at)}</p>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

export function MarketWeatherView({
  data,
}: Readonly<{ data: MissionControlData }>) {
  return (
    <div className="page-stack">
      <MarketWeatherPanel data={data} />
      <section>
        <SectionHeader eyebrow="Headlines" title="Catalyst pressure" />
        <div className="headline-list">
          {data.headline_pressure.headlines.map((headline) => (
            <article key={headline.headline_event_id}>
              <h3>{headline.title}</h3>
              <p>
                {headline.source} / {headline.ticker ?? "market-wide"} /{" "}
                {freshnessLabel(headline.published_at)}
              </p>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

export function PositionsOrdersView({
  data,
}: Readonly<{ data: MissionControlData }>) {
  return (
    <div className="page-stack">
      <SectionHeader
        eyebrow="Positions & Orders"
        title="Paper positions and broker request state"
        description="Order rows expose idempotency and lifecycle state without sensitive account data."
      />
      <div className="table-panel wide" role="table" aria-label="Positions">
        {data.positions.map((position) => (
          <div role="row" key={position.position_snapshot_id}>
            <span role="cell">{position.ticker}</span>
            <span role="cell">{position.asset_type}</span>
            <span role="cell">{position.quantity}</span>
            <span role="cell">{formatMoney(position.average_price)}</span>
            <span role="cell">{formatMoney(position.market_value)}</span>
          </div>
        ))}
      </div>
      <div
        className="table-panel wide"
        role="table"
        aria-label="Broker order requests"
      >
        {data.broker_order_requests.map((request) => (
          <div role="row" key={request.broker_order_request_id}>
            <span role="cell">{request.side}</span>
            <span role="cell">{request.order_type}</span>
            <span role="cell">{request.quantity}</span>
            <span role="cell">{request.idempotency_key}</span>
            <span role="cell">{request.limit_price ?? "no limit"}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function LearningLabView({
  data,
}: Readonly<{ data: MissionControlData }>) {
  return (
    <div className="page-stack">
      <SectionHeader
        eyebrow="Learning Lab"
        title="Labels, near misses, replay, and recommendations"
        description="Learning may recommend changes, but cannot mutate live policy, risk, broker behavior, or production prompts."
      />
      <section className="dashboard-grid">
        <div>
          <h2>Outcome labels</h2>
          {data.trade_outcomes.map((outcome) => (
            <article className="reason-row" key={outcome.trade_outcome_id}>
              <StatusBadge status="ok">{outcome.label}</StatusBadge>
              <div>
                <h3>{outcome.signal_id}</h3>
                <p>
                  P/L {formatMoney(outcome.realized_pnl)} / MFE{" "}
                  {formatMoney(outcome.max_favorable_excursion)}
                </p>
              </div>
            </article>
          ))}
        </div>
        <div>
          <h2>Near misses</h2>
          {data.near_misses.map((nearMiss) => (
            <article className="reason-row" key={nearMiss.near_miss_id}>
              <StatusBadge status="review">review</StatusBadge>
              <div>
                <h3>{nearMiss.signal_id}</h3>
                <p>{nearMiss.reason}</p>
              </div>
            </article>
          ))}
        </div>
      </section>
      <section className="dashboard-grid">
        <div>
          <h2>Replay reports</h2>
          {data.replay_reports.map((report) => (
            <article className="reason-row" key={report.replay_report_id}>
              <StatusBadge
                status={report.no_lookahead_verified ? "ok" : "blocked"}
              >
                {report.split}
              </StatusBadge>
              <div>
                <h3>{report.compared_decisions} decisions compared</h3>
                <p>{report.disagreement_count} disagreements found.</p>
              </div>
            </article>
          ))}
        </div>
        <div>
          <h2>Failure patterns</h2>
          {data.failure_patterns.map((pattern) => (
            <article className="reason-row" key={pattern.pattern_id}>
              <StatusBadge status="review">{pattern.severity}</StatusBadge>
              <div>
                <h3>{pattern.affected_strategy}</h3>
                <p>{pattern.summary}</p>
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

export function ModelHealthView({
  data,
}: Readonly<{ data: MissionControlData }>) {
  return (
    <div className="page-stack">
      <SectionHeader
        eyebrow="Model Health"
        title="Registry, evaluation, and promotion status"
        description="No trained model is implied unless a manifest and evaluation report support it."
      />
      <div className="status-matrix">
        {data.model_health.map((model) => (
          <article key={model.model_manifest_id}>
            <StatusBadge status={model.status}>{model.mode}</StatusBadge>
            <h3>{model.name}</h3>
            <p>{model.weakness}</p>
          </article>
        ))}
      </div>
      <div
        className="table-panel wide"
        role="table"
        aria-label="Model evaluation reports"
      >
        {data.model_evaluations.map((evaluation) => (
          <div role="row" key={evaluation.model_evaluation_report_id}>
            <span role="cell">{evaluation.model_manifest_id}</span>
            <span role="cell">{evaluation.labeled_outcome_count} labels</span>
            <span role="cell">
              {evaluation.promotion_approved
                ? "promotion approved"
                : "not promoted"}
            </span>
            <span role="cell">{evaluation.metrics.calibration}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function IncidentsControlsView({
  data,
}: Readonly<{ data: MissionControlData }>) {
  return (
    <div className="page-stack">
      <SectionHeader
        eyebrow="Incidents & Controls"
        title="Operator controls and unresolved incidents"
        description="Critical incidents and active kill switches halt live trading routes."
      />
      <section className="dashboard-grid">
        <div>
          <h2>Active incidents</h2>
          {data.incidents.length === 0 ? (
            <EmptyState
              title="No active incidents"
              detail="The incident queue is empty."
            />
          ) : (
            data.incidents.map((incident) => (
              <article className="reason-row" key={incident.system_incident_id}>
                <StatusBadge
                  status={incident.status === "open" ? "review" : "ok"}
                >
                  {incident.severity}
                </StatusBadge>
                <div>
                  <h3>{incident.summary}</h3>
                  <p>{freshnessLabel(incident.opened_at)}</p>
                </div>
              </article>
            ))
          )}
        </div>
        <div>
          <h2>Kill switches</h2>
          {data.controls.map((control) => (
            <article className="reason-row" key={control.id}>
              <StatusBadge
                status={control.status === "active" ? "active" : "review"}
              >
                {control.scope}
              </StatusBadge>
              <div>
                <h3>{control.target}</h3>
                <p>{control.detail}</p>
              </div>
            </article>
          ))}
        </div>
      </section>
      <section>
        <SectionHeader
          eyebrow="Provider circuit breakers"
          title="Provider health"
        />
        <div className="status-matrix">
          {data.provider_health.map((provider) => (
            <article key={provider.name}>
              <StatusBadge status={provider.status}>
                {provider.circuit_breaker}
              </StatusBadge>
              <h3>{provider.name}</h3>
              <p>{provider.freshness} freshness</p>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

export function SettingsView({ data }: Readonly<{ data: MissionControlData }>) {
  return (
    <div className="page-stack">
      <SectionHeader
        eyebrow="Settings"
        title="Tenant, subscription, and disclosure state"
        description="Settings are tenant scoped. Sensitive session and broker values stay redacted."
      />
      <section className="dashboard-grid">
        <dl className="fact-list">
          <div>
            <dt>Tenant</dt>
            <dd>{data.tenant.display_name}</dd>
          </div>
          <div>
            <dt>Role</dt>
            <dd>{data.session.role}</dd>
          </div>
          <div>
            <dt>Session token</dt>
            <dd>{data.session.token_redacted}</dd>
          </div>
        </dl>
        <dl className="fact-list">
          <div>
            <dt>Plan</dt>
            <dd>{data.subscription.plan_code}</dd>
          </div>
          <div>
            <dt>Risk disclosure</dt>
            <dd>
              {data.tenant.risk_disclosure_acknowledged
                ? "acknowledged"
                : "required"}
            </dd>
          </div>
          <div>
            <dt>Provider data disclosure</dt>
            <dd>
              {data.tenant.provider_data_disclaimer_acknowledged
                ? "acknowledged"
                : "required"}
            </dd>
          </div>
        </dl>
      </section>
    </div>
  );
}
