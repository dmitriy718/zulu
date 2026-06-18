import type { MissionControlData } from "./platform";

const now = "2026-06-18T13:45:00Z";
const soon = "2026-06-18T14:00:00Z";

const marketData = {
  snapshot_id: "md_msft_fixture_1",
  tenant_id: "tenant_1",
  ticker: "MSFT",
  bid: "421.20",
  ask: "421.44",
  last: "421.32",
  volume: 3820000,
  source: "fixture-provider",
  observed_at: now,
  expires_at: soon,
  received_at: now,
} as const;

const marketWeather = {
  market_weather_id: "mw_fixture_1",
  tenant_id: "tenant_1",
  regime: "balanced risk-on",
  volatility_regime: "normalizing",
  breadth_score: "0.56",
  risk_on_score: "0.61",
  as_of: now,
  expires_at: soon,
} as const;

const featureVector = {
  feature_vector_id: "fv_msft_fixture_1",
  tenant_id: "tenant_1",
  ticker: "MSFT",
  schema_version: "canonical_features_v1",
  feature_values: {
    "canonical_v1.trend_strength": "0.67",
    "canonical_v1.vwap_relationship": "0.58",
    "canonical_v1.relative_volume": "1.31",
    "canonical_v1.spread_quality": "0.82",
  },
  generated_at: now,
} as const;

export const fixtureMissionControlData: MissionControlData = {
  data_mode: "fixture",
  session: {
    tenant_id: "tenant_1",
    user_id: "user_owner",
    role: "owner",
    token_redacted: "toke...[REDACTED]",
  },
  tenant: {
    tenant_id: "tenant_1",
    display_name: "Zulu Demo Tenant",
    risk_disclosure_acknowledged: true,
    provider_data_disclaimer_acknowledged: true,
  },
  subscription: {
    tenant_id: "tenant_1",
    plan_code: "automation_paper",
    status: "active",
    allowed_modes: ["signal_station", "automation_station"],
    automation_enabled: true,
    live_trading_allowed: false,
  },
  market_weather: marketWeather,
  market_weather_components: [
    {
      label: "Index trend",
      state: "constructive",
      score: "0.64",
      impact:
        "Long signals require cleaner entry triggers, shorts need extra confirmation.",
    },
    {
      label: "Volatility",
      state: "normalizing",
      score: "0.48",
      impact:
        "Position sizing remains capped; stop distance is checked before routing.",
    },
    {
      label: "Breadth",
      state: "mixed participation",
      score: "0.56",
      impact:
        "Single-name signals are accepted only with clear liquidity support.",
    },
    {
      label: "Headline pressure",
      state: "elevated",
      score: "0.38",
      impact:
        "Catalyst-sensitive tickers carry a visible data-limitation note.",
    },
    {
      label: "Session timing",
      state: "mid-session",
      score: "0.71",
      impact:
        "Gap candidates are de-emphasized after opening behavior stabilizes.",
    },
    {
      label: "Liquidity",
      state: "acceptable",
      score: "0.79",
      impact:
        "Options signals still require explicit volume and open-interest checks.",
    },
  ],
  headline_pressure: {
    level: "medium",
    summary:
      "Provider metadata is complete for current fixture headlines; market-wide pressure remains elevated around rates and mega-cap earnings.",
    headlines: [
      {
        headline_event_id: "headline_msft_1",
        tenant_id: "tenant_1",
        ticker: "MSFT",
        title:
          "Mega-cap software names hold bid while index breadth stays mixed",
        source: "fixture-provider",
        url: null,
        sentiment_score: "0.180000",
        published_at: "2026-06-18T13:12:00Z",
        received_at: "2026-06-18T13:13:00Z",
      },
      {
        headline_event_id: "headline_macro_1",
        tenant_id: "tenant_1",
        ticker: null,
        title: "Treasury yields steady ahead of afternoon policy commentary",
        source: "fixture-provider",
        url: null,
        sentiment_score: "-0.080000",
        published_at: "2026-06-18T13:22:00Z",
        received_at: "2026-06-18T13:23:00Z",
      },
    ],
  },
  pipeline: [
    {
      stage: "Provider normalization",
      status: "ok",
      detail: "Fresh stock and option context accepted from fixture provider.",
      updated_at: now,
    },
    {
      stage: "Feature generation",
      status: "ok",
      detail: "canonical_features_v1 generated with stable hash.",
      updated_at: now,
    },
    {
      stage: "Quality gates",
      status: "ok",
      detail:
        "Stop loss, entry trigger, TP ladder, and decision trace present.",
      updated_at: now,
    },
    {
      stage: "Automation routing",
      status: "blocked",
      detail: "Live routing remains disabled; paper eligibility only.",
      updated_at: now,
    },
  ],
  automation: {
    tenant_id: "tenant_1",
    environment: "paper",
    paper_enabled: true,
    shadow_enabled: true,
    live_enabled: false,
    risk_envelope_id: "risk_default",
    disclosure:
      "Signals are informational. Automation remains user-directed and gate-controlled.",
  },
  risk_envelope: {
    risk_envelope_id: "risk_default",
    max_risk_per_trade: "0.010000",
    max_daily_loss: "0.030000",
    max_open_positions: 4,
    max_ticker_exposure: "0.150000",
    options_spread_limit: "0.080000",
  },
  eligibility: [
    {
      label: "Subscription mode",
      status: "passed",
      detail: "Automation Station is available for paper and shadow review.",
    },
    {
      label: "Live environment",
      status: "blocked",
      detail:
        "Live trading is disabled by default and not allowed by this plan.",
    },
    {
      label: "PolicyGate",
      status: "review",
      detail:
        "Eligible signals still require fresh policy decisions before routing.",
    },
    {
      label: "RiskGate",
      status: "review",
      detail:
        "Risk envelope must approve sizing, spread, stops, and duplicate checks.",
    },
  ],
  broker: {
    tenant_id: "tenant_1",
    broker_name: "paper",
    connected: true,
    environment: "paper",
    credential_configured: false,
    account_id_redacted: null,
  },
  provider_health: [
    {
      name: "fixture equities",
      status: "ok",
      freshness: "15 seconds",
      capabilities: ["quotes", "bars", "calendar"],
      circuit_breaker: "closed",
    },
    {
      name: "fixture options",
      status: "ok",
      freshness: "30 seconds",
      capabilities: ["chain", "quotes", "open interest"],
      circuit_breaker: "closed",
    },
    {
      name: "fixture headlines",
      status: "degraded",
      freshness: "4 minutes",
      capabilities: ["headlines", "ticker tags"],
      circuit_breaker: "closed",
    },
  ],
  model_health: [
    {
      model_manifest_id: "model_baseline_v1",
      name: "Baseline deterministic scorer",
      mode: "baseline",
      feature_schema_version: "canonical_features_v1",
      status: "ok",
      weakness: "No trained ML model is promoted; scores are rule-based.",
      last_evaluated_at: "2026-06-18T12:30:00Z",
    },
    {
      model_manifest_id: "model_shadow_v1",
      name: "Shadow evaluator",
      mode: "shadow",
      feature_schema_version: "canonical_features_v1",
      status: "degraded",
      weakness: "Awaiting more labeled outcomes before promotion review.",
      last_evaluated_at: "2026-06-18T11:15:00Z",
    },
  ],
  clean_signals: [
    {
      signal_id: "sig_msft_fixture_1",
      tenant_id: "tenant_1",
      asset_type: "stock",
      ticker: "MSFT",
      option_contract: null,
      direction: "long",
      timeframe: "intraday",
      entry_zone: { lower: "420.40", upper: "422.10" },
      entry_trigger:
        "Sustained trade above VWAP with spread under risk envelope limit.",
      stop_loss: "416.80",
      take_profit_levels: [
        { label: "TP1", price: "426.20", scale_out_fraction: "0.500000" },
        { label: "TP2", price: "431.00", scale_out_fraction: "0.500000" },
      ],
      position_sizing_hint: {
        max_risk_fraction: "0.010000",
        notional_cap: "7500.00",
        rationale: "Capped by paper risk envelope and mixed market breadth.",
      },
      confidence_score: "0.680000",
      risk_score: "0.310000",
      quality_score: "0.720000",
      market_weather: marketWeather,
      market_data_snapshot: marketData,
      headline_context: [
        {
          headline_event_id: "headline_msft_1",
          relevance:
            "Sector context supports attention but does not verify outcome.",
        },
      ],
      technical_context:
        "VWAP reclaim with constructive trend and acceptable spread quality.",
      volatility_context:
        "Realized volatility is normalizing; stop distance remains explicit.",
      liquidity_context:
        "Stock liquidity accepted; options routing would require separate contract metadata.",
      upside_thesis:
        "Continuation can hold if VWAP remains support and breadth improves.",
      downside_risk:
        "Mixed breadth and headline pressure can reverse intraday continuation.",
      invalidation_conditions: [
        "Trade below stop loss",
        "Spread quality fails risk envelope",
        "Market weather shifts to risk-off",
      ],
      model_manifest_id: "model_baseline_v1",
      feature_schema_version: "canonical_features_v1",
      feature_hash:
        "6d3b2a83e44e52a89c8d0f1a4f3eaa5f3c1ad3d772b4ce5ad00c61b8db7a7f4b",
      feature_vector: featureVector,
      policy_status: "pending",
      created_at: now,
      expires_at: soon,
      decision_trace: [
        {
          stage: "context",
          decision: "accepted",
          reason:
            "Fresh fixture market context and market weather are available.",
          at: now,
        },
        {
          stage: "quality_gate",
          decision: "accepted",
          reason:
            "Entry trigger, stop loss, TP ladder, and risk context are present.",
          at: now,
        },
        {
          stage: "delivery",
          decision: "delivered_to_signal_station",
          reason:
            "Signal is visible for review; automation requires PolicyGate.",
          at: now,
        },
      ],
    },
  ],
  policy_decisions: [
    {
      policy_decision_id: "policy_sig_msft_fixture_1",
      tenant_id: "tenant_1",
      signal_id: "sig_msft_fixture_1",
      status: "approved",
      reason:
        "Signal Station delivery allowed; Automation Station requires risk review.",
      policy_version: "policy_v1",
      decided_at: now,
    },
  ],
  risk_decisions: [
    {
      risk_decision_id: "risk_sig_msft_fixture_1",
      tenant_id: "tenant_1",
      signal_id: "sig_msft_fixture_1",
      status: "rejected",
      reason: "Live route blocked because live trading is disabled.",
      risk_version: "risk_v1",
      max_loss: "75.00",
      decided_at: now,
    },
  ],
  execution_intents: [
    {
      execution_intent_id: "intent_paper_1",
      tenant_id: "tenant_1",
      signal_id: "sig_msft_fixture_1",
      policy_decision_id: "policy_sig_msft_fixture_1",
      risk_decision_id: "risk_sig_msft_fixture_1",
      terminal_state: "risk_rejected",
      requested_at: now,
    },
  ],
  broker_order_requests: [
    {
      broker_order_request_id: "bor_paper_1",
      tenant_id: "tenant_1",
      execution_intent_id: "intent_paper_1",
      idempotency_key: "idem_paper_msft_0001",
      side: "buy",
      order_type: "limit",
      quantity: "10",
      limit_price: "421.50",
      created_at: now,
    },
  ],
  order_lifecycle_events: [
    {
      order_lifecycle_event_id: "ole_paper_1",
      tenant_id: "tenant_1",
      broker_order_request_id: "bor_paper_1",
      status: "requested",
      occurred_at: now,
      broker_event_id: null,
      reconciled_at: null,
      system_incident_id: null,
      details: { mode: "paper", route: "blocked before live broker" },
    },
  ],
  positions: [
    {
      position_snapshot_id: "pos_msft_fixture_1",
      tenant_id: "tenant_1",
      ticker: "MSFT",
      asset_type: "stock",
      quantity: "10",
      average_price: "419.80",
      market_value: "4213.20",
      as_of: now,
    },
  ],
  ledger: [
    {
      id: "ledger_1",
      occurred_at: now,
      type: "signal",
      status: "delivered_to_signal_station",
      actor: "signal-intelligence",
      summary: "Clean MSFT signal delivered to Signal Station.",
      trace: [
        "context accepted",
        "quality gate accepted",
        "durable outbox published",
      ],
    },
    {
      id: "ledger_2",
      occurred_at: now,
      type: "policy",
      status: "approved",
      actor: "policy-gate",
      summary: "Signal review allowed for tenant subscription mode.",
      trace: [
        "subscription checked",
        "data freshness checked",
        "incident mode checked",
      ],
    },
    {
      id: "ledger_3",
      occurred_at: now,
      type: "risk",
      status: "rejected",
      actor: "risk-gate",
      summary: "Live execution blocked because live trading is disabled.",
      trace: [
        "risk envelope checked",
        "live plan checked",
        "broker route blocked",
      ],
    },
    {
      id: "ledger_4",
      occurred_at: "2026-06-18T13:31:00Z",
      type: "audit",
      status: "open",
      actor: "operator",
      summary: "Provider latency incident remains visible for operator review.",
      trace: ["incident opened", "circuit breaker monitored"],
    },
  ],
  trade_outcomes: [
    {
      trade_outcome_id: "outcome_1",
      tenant_id: "tenant_1",
      signal_id: "sig_prior_1",
      realized_pnl: "82.50",
      max_adverse_excursion: "24.00",
      max_favorable_excursion: "131.20",
      label: "partial_take_profit",
      labeled_at: "2026-06-18T12:10:00Z",
    },
  ],
  near_misses: [
    {
      near_miss_id: "near_1",
      tenant_id: "tenant_1",
      signal_id: "sig_skipped_1",
      reason: "Entry trigger fired after signal expiration.",
      would_have_triggered: true,
      labeled_at: "2026-06-18T12:42:00Z",
    },
  ],
  replay_reports: [
    {
      replay_report_id: "replay_shadow_1",
      split: "shadow",
      compared_decisions: 48,
      disagreement_count: 7,
      no_lookahead_verified: true,
      created_at: "2026-06-18T12:50:00Z",
    },
  ],
  failure_patterns: [
    {
      pattern_id: "pattern_1",
      severity: "medium",
      summary:
        "VWAP reclaim candidates degrade when breadth is mixed and headline pressure rises.",
      affected_strategy: "vwap_reclaim",
      recommended_action:
        "Create shadow evaluation task with stricter breadth floor.",
    },
  ],
  candidate_improvements: [
    {
      improvement_id: "improve_1",
      status: "evaluation_task_created",
      summary:
        "Reduce confidence contribution from relative volume during elevated headline pressure.",
      required_gate: "shadow evaluation before paper consideration",
    },
  ],
  model_manifests: [
    {
      model_manifest_id: "model_baseline_v1",
      tenant_id: "tenant_1",
      model_name: "Baseline deterministic scorer",
      model_version: "1.0.0",
      feature_schema_version: "canonical_features_v1",
      artifact_uri: "registry://baseline/deterministic",
      training_data_hash: "not-trained-baseline",
      created_at: "2026-06-18T00:00:00Z",
    },
  ],
  model_evaluations: [
    {
      model_evaluation_report_id: "eval_baseline_1",
      tenant_id: "tenant_1",
      model_manifest_id: "model_baseline_v1",
      evaluation_window_start: "2026-06-01T00:00:00Z",
      evaluation_window_end: "2026-06-18T00:00:00Z",
      labeled_outcome_count: 32,
      metrics: {
        calibration: "insufficient_labeled_data",
        drift: "watch",
      },
      promotion_approved: false,
      created_at: "2026-06-18T12:00:00Z",
    },
  ],
  incidents: [
    {
      system_incident_id: "incident_provider_latency",
      tenant_id: "tenant_1",
      severity: "low",
      status: "open",
      summary: "Headline provider latency above normal fixture threshold.",
      opened_at: "2026-06-18T13:31:00Z",
      resolved_at: null,
    },
  ],
  controls: [
    {
      id: "control_tenant",
      scope: "tenant",
      target: "tenant_1",
      status: "ready",
      detail: "Tenant kill switch available to operators.",
    },
    {
      id: "control_live",
      scope: "system",
      target: "live-trading",
      status: "active",
      detail: "Live trading is disabled by default.",
    },
    {
      id: "control_broker",
      scope: "broker",
      target: "paper",
      status: "ready",
      detail: "Paper broker route available after PolicyGate and RiskGate.",
    },
  ],
  audit_events: [
    {
      audit_event_id: "audit_delivery_1",
      tenant_id: "tenant_1",
      actor_id: "signal-intelligence",
      action: "signal.delivered",
      entity_type: "clean_signal",
      entity_id: "sig_msft_fixture_1",
      decision: "accepted",
      correlation_id: "req_fixture_1",
      occurred_at: now,
      details: { route: "signal_station", token: "[REDACTED]" },
    },
  ],
};
