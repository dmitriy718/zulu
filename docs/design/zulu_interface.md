# Zulu Interface

Zulu’s web interface is a trading mission-control surface for stocks/options intelligence and risk-governed automation.

## Design Direction

- Dense, operational, and decision-oriented rather than a marketing dashboard.
- Risk, uncertainty, data freshness, and decision trace are first-class UI elements.
- Desktop workflows are optimized for scanning; mobile layouts preserve all controls and context.
- The interface uses a 2026 command-center treatment: dark liquid-glass panels, translucent floating guard surfaces, scanline/grid depth, icon-led controls, and high-contrast risk accents.
- The palette uses graphite, cyan, operational green, warning amber, red risk states, and blue/violet secondary accents. It avoids generic black-and-purple SaaS gradients and profit-oriented styling.
- Cards retain tight 8px radius geometry so the product feels precise rather than decorative.

## Product Structure

Primary navigation:

- Command Center
- Signal Station
- Automation Station
- Market Weather
- Decision Ledger
- Positions & Orders
- Learning Lab
- Model Health
- Incidents & Controls
- Settings

## Data Rules

- Components consume typed contract or platform models from `apps/web/lib/contracts.ts` and `apps/web/lib/platform.ts`.
- Local development data is available only through explicit `fixture` data mode in `apps/web/lib/apiClient.ts`.
- Fixture mode is visible in the header so users do not confuse local data with live market or broker state.
- UI copy must distinguish informational signals from user-directed automation settings.

## Safety Surfaces

- Live trading is shown as disabled by default.
- Automation pages show Paper, Shadow, and Live mode separately.
- A floating gate console keeps PolicyGate, RiskGate, and live-disabled state visible across the app.
- Broker and order views expose idempotency and lifecycle state without account identifiers.
- Signal cards show entry zone, trigger, stop loss, take-profit ladder, confidence, risk, quality, thesis, downside risk, market weather, and data limitations.
- Decision Ledger shows chronological signal, policy, risk, broker, override, and audit traces.

## UI Package Choices

- `lucide-react` supplies consistent control and status icons.
- `clsx` keeps conditional status class composition explicit.
- `tailwindcss` with `@tailwindcss/postcss` provides the current CSS pipeline baseline while Zulu keeps custom product-specific classes for the command-center surface.
- `motion` is available for future client-side micro-interactions; current critical status surfaces rely on CSS so server-rendered pages remain simple and reliable.

## Accessibility

- The app uses semantic landmarks, headings, table roles, focus-visible outlines, and text labels for state.
- Status is not communicated by color alone; badges include readable text.
- Layouts collapse to single-column views on small screens without hiding risk disclosures.

## Current Limitations

- The interface currently uses explicit fixture mode for local development.
- API aggregation into a single mission-control payload is not enabled yet.
- No sensitive values are logged or displayed; fixture session tokens remain redacted.
