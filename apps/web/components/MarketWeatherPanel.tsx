import { CloudSun, Compass, Waves } from "lucide-react";

import type { MissionControlData } from "../lib/platform";
import { formatPercent, freshnessLabel } from "../lib/platform";
import { StatusBadge } from "./UI";

export function MarketWeatherPanel({
  data,
}: Readonly<{ data: MissionControlData }>) {
  return (
    <section className="weather-panel" aria-labelledby="market-weather-title">
      <div className="section-header">
        <p className="eyebrow">Market Weather</p>
        <h2 id="market-weather-title">
          <CloudSun aria-hidden="true" size={28} />
          {data.market_weather.regime}
        </h2>
        <p>
          {data.market_weather.volatility_regime} volatility,{" "}
          {formatPercent(data.market_weather.risk_on_score)} risk-on posture.
        </p>
      </div>
      <div className="weather-grid">
        {data.market_weather_components.map((component) => (
          <article key={component.label} className="weather-cell">
            <div>
              <h3>{component.label}</h3>
              <StatusBadge status="review">{component.state}</StatusBadge>
            </div>
            <strong>
              <Compass aria-hidden="true" size={18} />
              {formatPercent(component.score)}
            </strong>
            <p>{component.impact}</p>
          </article>
        ))}
      </div>
      <p className="freshness-badge">
        <Waves aria-hidden="true" size={15} />
        {freshnessLabel(data.market_weather.as_of)}
      </p>
    </section>
  );
}
