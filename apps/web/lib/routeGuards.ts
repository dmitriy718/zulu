import { getMissionControlData } from "./apiClient";
import type { DataMode, MissionControlData, ProductMode } from "./platform";
import { hasProductMode } from "./platform";

export interface RouteContext {
  data: MissionControlData;
  mode: DataMode;
}

export async function loadRouteContext(
  requiredMode?: ProductMode,
): Promise<RouteContext> {
  const mode = resolveDataMode();
  const data = await getMissionControlData({
    tenantId: "tenant_1",
    mode,
    token: process.env.ZULU_WEB_FIXTURE_TOKEN,
  });

  if (requiredMode && !hasProductMode(data.subscription, requiredMode)) {
    return {
      mode,
      data: {
        ...data,
        automation: {
          ...data.automation,
          live_enabled: false,
        },
      },
    };
  }

  return { data, mode };
}

export function resolveDataMode(): DataMode {
  return process.env.ZULU_WEB_DATA_MODE === "api" ? "api" : "fixture";
}
