import { describe, expect, it } from "vitest";

import type { BrokerOrderRequest, CleanSignalV1 } from "../lib/contracts";

describe("mirrored contract types", () => {
  it("requires broker order idempotency keys at compile time", () => {
    const request = {
      broker_order_request_id: "bor_1",
      tenant_id: "tenant_1",
      execution_intent_id: "intent_1",
      idempotency_key: "idem_1234567890123456",
      side: "buy",
      order_type: "limit",
      quantity: "1",
      limit_price: "10.00",
      created_at: "2026-06-18T00:00:00Z",
    } satisfies BrokerOrderRequest;

    expect(request.idempotency_key).toContain("idem_");
  });

  it("mirrors clean signal required safety fields", () => {
    const keys: Array<keyof CleanSignalV1> = [
      "signal_id",
      "tenant_id",
      "asset_type",
      "stop_loss",
      "entry_zone",
      "entry_trigger",
      "feature_hash",
      "decision_trace",
    ];

    expect(keys).toContain("stop_loss");
  });
});
