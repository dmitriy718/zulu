import { CircleSlash, LockKeyhole, Radar, ShieldCheck } from "lucide-react";

import type { MissionControlData } from "../lib/platform";
import { formatPercent } from "../lib/platform";
import { StatusBadge } from "./UI";

export function AutomationGatePanel({
  data,
}: Readonly<{ data: MissionControlData }>) {
  return (
    <section
      className="automation-panel"
      aria-labelledby="automation-gates-title"
    >
      <div className="section-header">
        <p className="eyebrow">Automation Station</p>
        <h2 id="automation-gates-title">
          <LockKeyhole aria-hidden="true" size={26} />
          Eligibility checklist
        </h2>
        <p>{data.automation.disclosure}</p>
      </div>

      <div className="mode-grid" aria-label="Automation mode status">
        <div>
          <span>
            <Radar aria-hidden="true" size={14} />
            Paper
          </span>
          <strong>
            {data.automation.paper_enabled ? "Enabled" : "Disabled"}
          </strong>
        </div>
        <div>
          <span>
            <ShieldCheck aria-hidden="true" size={14} />
            Shadow
          </span>
          <strong>
            {data.automation.shadow_enabled ? "Enabled" : "Disabled"}
          </strong>
        </div>
        <div>
          <span>
            <CircleSlash aria-hidden="true" size={14} />
            Live
          </span>
          <strong>
            {data.automation.live_enabled ? "Enabled" : "Disabled"}
          </strong>
        </div>
      </div>

      <div className="checklist">
        {data.eligibility.map((check) => (
          <article key={check.label} className="check-row">
            <StatusBadge status={check.status}>{check.status}</StatusBadge>
            <div>
              <h3>{check.label}</h3>
              <p>{check.detail}</p>
            </div>
          </article>
        ))}
      </div>

      <dl className="risk-envelope">
        <div>
          <dt>Max risk/trade</dt>
          <dd>{formatPercent(data.risk_envelope.max_risk_per_trade)}</dd>
        </div>
        <div>
          <dt>Daily loss cap</dt>
          <dd>{formatPercent(data.risk_envelope.max_daily_loss)}</dd>
        </div>
        <div>
          <dt>Max open positions</dt>
          <dd>{data.risk_envelope.max_open_positions}</dd>
        </div>
        <div>
          <dt>Options spread limit</dt>
          <dd>{formatPercent(data.risk_envelope.options_spread_limit)}</dd>
        </div>
      </dl>
    </section>
  );
}
