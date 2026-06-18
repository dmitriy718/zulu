import {
  ArrowDownToLine,
  Crosshair,
  Gauge,
  ListTree,
  ShieldAlert,
  Sparkles,
  Timer,
} from "lucide-react";

import type { CleanSignalV1 } from "../lib/contracts";
import { formatMoney, formatPercent, freshnessLabel } from "../lib/platform";
import { StatusBadge } from "./UI";

export function SignalCard({
  signal,
  detailed = false,
}: Readonly<{ signal: CleanSignalV1; detailed?: boolean }>) {
  return (
    <article
      className="signal-card"
      aria-labelledby={`${signal.signal_id}-title`}
    >
      <div className="signal-card-header">
        <div>
          <span className="ticker">
            <Sparkles aria-hidden="true" size={22} />
            {signal.ticker}
          </span>
          <h2 id={`${signal.signal_id}-title`}>
            {signal.direction} {signal.asset_type} / {signal.timeframe}
          </h2>
        </div>
        <StatusBadge status="review">{signal.policy_status}</StatusBadge>
      </div>

      <dl className="score-grid" aria-label={`${signal.ticker} signal scores`}>
        <div>
          <dt>
            <Gauge aria-hidden="true" size={15} />
            Confidence
          </dt>
          <dd>{formatPercent(signal.confidence_score)}</dd>
        </div>
        <div>
          <dt>
            <ShieldAlert aria-hidden="true" size={15} />
            Risk
          </dt>
          <dd>{formatPercent(signal.risk_score)}</dd>
        </div>
        <div>
          <dt>
            <ListTree aria-hidden="true" size={15} />
            Quality
          </dt>
          <dd>{formatPercent(signal.quality_score)}</dd>
        </div>
      </dl>

      <div className="signal-anatomy">
        <div>
          <span>
            <Crosshair aria-hidden="true" size={14} />
            Entry zone
          </span>
          <strong>
            {formatMoney(signal.entry_zone.lower)} -{" "}
            {formatMoney(signal.entry_zone.upper)}
          </strong>
        </div>
        <div>
          <span>
            <ArrowDownToLine aria-hidden="true" size={14} />
            Stop loss
          </span>
          <strong>{formatMoney(signal.stop_loss)}</strong>
        </div>
        <div>
          <span>
            <Timer aria-hidden="true" size={14} />
            Trigger
          </span>
          <strong>{signal.entry_trigger}</strong>
        </div>
      </div>

      <div className="tp-ladder" aria-label="Take profit ladder">
        {signal.take_profit_levels.map((level) => (
          <span key={level.label}>
            {level.label}: {formatMoney(level.price)} /{" "}
            {formatPercent(level.scale_out_fraction)}
          </span>
        ))}
      </div>

      {detailed ? (
        <div className="detail-grid">
          <section>
            <h3>Upside Thesis</h3>
            <p>{signal.upside_thesis}</p>
          </section>
          <section>
            <h3>Downside Risk</h3>
            <p>{signal.downside_risk}</p>
          </section>
          <section>
            <h3>Market Weather Impact</h3>
            <p>{signal.market_weather.regime}</p>
          </section>
          <section>
            <h3>Data Limitations</h3>
            <p>{signal.liquidity_context}</p>
          </section>
        </div>
      ) : null}

      <footer className="signal-footer">
        <span>{freshnessLabel(signal.created_at)}</span>
        <span>expires {freshnessLabel(signal.expires_at)}</span>
      </footer>
    </article>
  );
}
