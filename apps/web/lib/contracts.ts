export type AssetType = "stock" | "option";
export type OptionType = "call" | "put";
export type SignalDirection = "long" | "short";
export type Timeframe = "intraday" | "swing" | "position";
export type PolicyStatus = "pending" | "approved" | "rejected";
export type DecisionStatus = "approved" | "rejected";
export type AcceptedSignalTerminalState =
  | "delivered_to_signal_station"
  | "execution_attempted"
  | "policy_rejected"
  | "risk_rejected"
  | "expired"
  | "cancelled_by_user"
  | "system_blocked";
export type OrderSide = "buy" | "sell";
export type OrderType = "market" | "limit" | "stop" | "stop_limit";
export type OrderLifecycleStatus =
  | "requested"
  | "submitted"
  | "acknowledged"
  | "partially_filled"
  | "filled"
  | "cancelled"
  | "rejected"
  | "reconciled"
  | "unresolved";

export interface EntryZone {
  lower: string;
  upper: string;
}

export interface TakeProfitLevel {
  label: string;
  price: string;
  scale_out_fraction: string;
}

export interface PositionSizingHint {
  max_risk_fraction: string;
  notional_cap: string;
  rationale: string;
}

export interface MarketDataSnapshot {
  snapshot_id: string;
  tenant_id: string;
  ticker: string;
  bid: string;
  ask: string;
  last: string;
  volume: number;
  source: string;
  observed_at: string;
  expires_at: string;
  received_at: string;
}

export interface OptionContractSnapshot {
  option_contract_id: string;
  tenant_id: string;
  underlying_ticker: string;
  option_symbol: string;
  option_type: OptionType;
  strike: string;
  expiration_date: string;
  multiplier: number;
  bid: string;
  ask: string;
  delta?: string | null;
  gamma?: string | null;
  theta?: string | null;
  vega?: string | null;
  implied_volatility?: string | null;
  open_interest: number;
  volume: number;
  source: string;
  observed_at: string;
}

export interface HeadlineEvent {
  headline_event_id: string;
  tenant_id: string;
  ticker?: string | null;
  title: string;
  source: string;
  url?: string | null;
  sentiment_score: string;
  published_at: string;
  received_at: string;
}

export interface MarketWeatherSnapshot {
  market_weather_id: string;
  tenant_id: string;
  regime: string;
  volatility_regime: string;
  breadth_score: string;
  risk_on_score: string;
  as_of: string;
  expires_at: string;
}

export interface CanonicalFeatureVectorV1 {
  feature_vector_id: string;
  tenant_id: string;
  ticker: string;
  schema_version: "canonical_features_v1";
  feature_values: Record<string, string>;
  generated_at: string;
}

export interface StrategyCandidate {
  strategy_candidate_id: string;
  tenant_id: string;
  asset_type: AssetType;
  ticker: string;
  direction: SignalDirection;
  timeframe: Timeframe;
  feature_vector: CanonicalFeatureVectorV1;
  rationale: string;
  created_at: string;
}

export interface HeadlineContextItem {
  headline_event_id: string;
  relevance: string;
}

export interface DecisionTraceItem {
  stage: string;
  decision: string;
  reason: string;
  at: string;
}

export interface CleanSignalV1 {
  signal_id: string;
  tenant_id: string;
  asset_type: AssetType;
  ticker: string;
  option_contract?: OptionContractSnapshot | null;
  direction: SignalDirection;
  timeframe: Timeframe;
  entry_zone: EntryZone;
  entry_trigger: string;
  stop_loss: string;
  take_profit_levels: TakeProfitLevel[];
  position_sizing_hint: PositionSizingHint;
  confidence_score: string;
  risk_score: string;
  quality_score: string;
  market_weather: MarketWeatherSnapshot;
  market_data_snapshot: MarketDataSnapshot;
  headline_context: HeadlineContextItem[];
  technical_context: string;
  volatility_context: string;
  liquidity_context: string;
  upside_thesis: string;
  downside_risk: string;
  invalidation_conditions: string[];
  model_manifest_id: string;
  feature_schema_version: "canonical_features_v1";
  feature_hash: string;
  feature_vector: CanonicalFeatureVectorV1;
  policy_status: PolicyStatus;
  created_at: string;
  expires_at: string;
  decision_trace: DecisionTraceItem[];
}

export interface PolicyDecision {
  policy_decision_id: string;
  tenant_id: string;
  signal_id: string;
  status: DecisionStatus;
  reason: string;
  policy_version: string;
  decided_at: string;
}

export interface RiskDecision {
  risk_decision_id: string;
  tenant_id: string;
  signal_id: string;
  status: DecisionStatus;
  reason: string;
  risk_version: string;
  max_loss: string;
  decided_at: string;
}

export interface ExecutionIntent {
  execution_intent_id: string;
  tenant_id: string;
  signal_id: string;
  policy_decision_id: string;
  risk_decision_id: string;
  terminal_state: AcceptedSignalTerminalState;
  requested_at: string;
}

export interface BrokerOrderRequest {
  broker_order_request_id: string;
  tenant_id: string;
  execution_intent_id: string;
  idempotency_key: string;
  side: OrderSide;
  order_type: OrderType;
  quantity: string;
  limit_price?: string | null;
  created_at: string;
}

export interface OrderLifecycleEvent {
  order_lifecycle_event_id: string;
  tenant_id: string;
  broker_order_request_id: string;
  status: OrderLifecycleStatus;
  occurred_at: string;
  broker_event_id?: string | null;
  reconciled_at?: string | null;
  system_incident_id?: string | null;
  details: Record<string, unknown>;
}

export interface PositionSnapshot {
  position_snapshot_id: string;
  tenant_id: string;
  ticker: string;
  asset_type: AssetType;
  quantity: string;
  average_price: string;
  market_value: string;
  as_of: string;
}

export interface TradeOutcomeLabel {
  trade_outcome_id: string;
  tenant_id: string;
  signal_id: string;
  realized_pnl: string;
  max_adverse_excursion: string;
  max_favorable_excursion: string;
  label: string;
  labeled_at: string;
}

export interface NearMissLabel {
  near_miss_id: string;
  tenant_id: string;
  signal_id: string;
  reason: string;
  would_have_triggered: boolean;
  labeled_at: string;
}

export interface ModelManifest {
  model_manifest_id: string;
  tenant_id: string;
  model_name: string;
  model_version: string;
  feature_schema_version: "canonical_features_v1";
  artifact_uri: string;
  training_data_hash: string;
  created_at: string;
}

export interface ModelEvaluationReport {
  model_evaluation_report_id: string;
  tenant_id: string;
  model_manifest_id: string;
  evaluation_window_start: string;
  evaluation_window_end: string;
  labeled_outcome_count: number;
  metrics: Record<string, string>;
  promotion_approved: boolean;
  created_at: string;
}

export interface UserOverrideEvent {
  user_override_event_id: string;
  tenant_id: string;
  user_id: string;
  action:
    | "disable_automation"
    | "cancel_signal"
    | "block_instrument"
    | "resume_automation";
  reason: string;
  occurred_at: string;
}

export interface SystemIncident {
  system_incident_id: string;
  tenant_id: string;
  severity: "low" | "medium" | "high" | "critical";
  status: "open" | "mitigated" | "resolved";
  summary: string;
  opened_at: string;
  resolved_at?: string | null;
}

export interface AuditEvent {
  audit_event_id: string;
  tenant_id: string;
  actor_id: string;
  action: string;
  entity_type: string;
  entity_id: string;
  decision: string;
  correlation_id: string;
  occurred_at: string;
  details: Record<string, unknown>;
}

export type ProductMode = "signal_station" | "automation_station";
export type PlanCode = "signal_basic" | "automation_paper" | "automation_live";
export type SubscriptionStatus = "active" | "pending_change" | "cancelled";
export type AutomationEnvironment = "paper" | "shadow" | "live";

export interface PlanStatus {
  tenant_id: string;
  plan_code: PlanCode;
  status: SubscriptionStatus;
  allowed_modes: ProductMode[];
  automation_enabled: boolean;
  live_trading_allowed: boolean;
}
