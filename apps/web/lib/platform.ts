import type {
  AcceptedSignalTerminalState,
  AuditEvent,
  AutomationEnvironment,
  BrokerOrderRequest,
  CleanSignalV1,
  ExecutionIntent,
  HeadlineEvent,
  MarketWeatherSnapshot,
  ModelEvaluationReport,
  ModelManifest,
  NearMissLabel,
  OrderLifecycleEvent,
  PlanStatus,
  PolicyDecision,
  PositionSnapshot,
  ProductMode,
  RiskDecision,
  SystemIncident,
  TradeOutcomeLabel,
} from "./contracts";

export type { ProductMode } from "./contracts";

export type Role =
  | "owner"
  | "admin"
  | "trader"
  | "viewer"
  | "operator"
  | "support-readonly";

export type DataMode = "fixture" | "api";

export type ServiceState = "ok" | "degraded" | "blocked" | "offline";

export interface UserSession {
  tenant_id: string;
  user_id: string;
  role: Role;
  token_redacted: string;
}

export interface TenantSettings {
  tenant_id: string;
  display_name: string;
  risk_disclosure_acknowledged: boolean;
  provider_data_disclaimer_acknowledged: boolean;
}

export interface ProviderHealth {
  name: string;
  status: ServiceState;
  freshness: string;
  capabilities: string[];
  circuit_breaker: "closed" | "open" | "half_open";
}

export interface ModelHealth {
  model_manifest_id: string;
  name: string;
  mode: "baseline" | "shadow" | "paper" | "approved" | "blocked";
  feature_schema_version: "canonical_features_v1";
  status: ServiceState;
  weakness: string;
  last_evaluated_at: string;
}

export interface SignalPipelineStatus {
  stage: string;
  status: ServiceState;
  detail: string;
  updated_at: string;
}

export interface AutomationSettings {
  tenant_id: string;
  environment: AutomationEnvironment;
  paper_enabled: boolean;
  shadow_enabled: boolean;
  live_enabled: boolean;
  risk_envelope_id: string;
  disclosure: string;
}

export interface RiskEnvelope {
  risk_envelope_id: string;
  max_risk_per_trade: string;
  max_daily_loss: string;
  max_open_positions: number;
  max_ticker_exposure: string;
  options_spread_limit: string;
}

export interface EligibilityCheck {
  label: string;
  status: "passed" | "blocked" | "review";
  detail: string;
}

export interface BrokerConnectionStatus {
  tenant_id: string;
  broker_name: string;
  connected: boolean;
  environment: AutomationEnvironment;
  credential_configured: boolean;
  account_id_redacted: string | null;
}

export interface BlockedSignalExplanation {
  signal_id: string;
  ticker: string;
  blocked_by: "policy" | "risk" | "data" | "incident";
  reason: string;
}

export interface OrderTimelineItem {
  label: string;
  status: ServiceState;
  at: string;
  detail: string;
}

export interface MarketWeatherComponent {
  label: string;
  state: string;
  score: string;
  impact: string;
}

export interface DecisionLedgerEntry {
  id: string;
  occurred_at: string;
  type: "signal" | "policy" | "risk" | "broker" | "override" | "audit";
  status: AcceptedSignalTerminalState | "approved" | "rejected" | "open";
  actor: string;
  summary: string;
  trace: string[];
}

export interface LearningReplayReport {
  replay_report_id: string;
  split: "training" | "validation" | "test" | "shadow";
  compared_decisions: number;
  disagreement_count: number;
  no_lookahead_verified: boolean;
  created_at: string;
}

export interface FailurePattern {
  pattern_id: string;
  severity: "low" | "medium" | "high";
  summary: string;
  affected_strategy: string;
  recommended_action: string;
}

export interface CandidateImprovement {
  improvement_id: string;
  status: "proposed" | "evaluation_task_created" | "blocked";
  summary: string;
  required_gate: string;
}

export interface IncidentControl {
  id: string;
  scope: "system" | "tenant" | "ticker" | "strategy" | "model" | "broker";
  target: string;
  status: "active" | "ready" | "blocked";
  detail: string;
}

export interface MissionControlData {
  data_mode: DataMode;
  session: UserSession;
  tenant: TenantSettings;
  subscription: PlanStatus;
  market_weather: MarketWeatherSnapshot;
  market_weather_components: MarketWeatherComponent[];
  headline_pressure: {
    level: "low" | "medium" | "high";
    summary: string;
    headlines: HeadlineEvent[];
  };
  pipeline: SignalPipelineStatus[];
  automation: AutomationSettings;
  risk_envelope: RiskEnvelope;
  eligibility: EligibilityCheck[];
  broker: BrokerConnectionStatus;
  provider_health: ProviderHealth[];
  model_health: ModelHealth[];
  clean_signals: CleanSignalV1[];
  policy_decisions: PolicyDecision[];
  risk_decisions: RiskDecision[];
  execution_intents: ExecutionIntent[];
  broker_order_requests: BrokerOrderRequest[];
  order_lifecycle_events: OrderLifecycleEvent[];
  positions: PositionSnapshot[];
  ledger: DecisionLedgerEntry[];
  trade_outcomes: TradeOutcomeLabel[];
  near_misses: NearMissLabel[];
  replay_reports: LearningReplayReport[];
  failure_patterns: FailurePattern[];
  candidate_improvements: CandidateImprovement[];
  model_manifests: ModelManifest[];
  model_evaluations: ModelEvaluationReport[];
  incidents: SystemIncident[];
  controls: IncidentControl[];
  audit_events: AuditEvent[];
}

export function hasProductMode(plan: PlanStatus, mode: ProductMode): boolean {
  return plan.allowed_modes.includes(mode);
}

export function formatPercent(decimalText: string): string {
  const value = Number(decimalText);
  if (!Number.isFinite(value)) {
    return "Unavailable";
  }
  return `${Math.round(value * 100)}%`;
}

export function formatMoney(decimalText: string): string {
  const value = Number(decimalText);
  if (!Number.isFinite(value)) {
    return "Unavailable";
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(value);
}

export function freshnessLabel(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return "freshness unavailable";
  }
  return `as of ${date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })}`;
}
