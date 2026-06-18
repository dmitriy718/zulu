import { fixtureMissionControlData } from "./fixtureData";
import type { DataMode, MissionControlData } from "./platform";

export class ApiClientError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiClientError";
  }
}

export interface MissionControlRequest {
  tenantId: string;
  token?: string;
  mode: DataMode;
}

export async function getMissionControlData({
  tenantId,
  token,
  mode,
}: MissionControlRequest): Promise<MissionControlData> {
  if (mode === "fixture") {
    return fixtureMissionControlData;
  }

  const baseUrl = process.env.NEXT_PUBLIC_ZULU_API_BASE_URL;
  if (!baseUrl) {
    throw new ApiClientError(
      "API mode requires NEXT_PUBLIC_ZULU_API_BASE_URL.",
    );
  }
  if (!token) {
    throw new ApiClientError(
      "API mode requires an authenticated session token.",
    );
  }

  const headers = { Authorization: `Bearer ${token}` };
  const [subscriptionResponse, signalsResponse, weatherResponse] =
    await Promise.all([
      fetch(`${baseUrl}/tenants/${tenantId}/subscription`, {
        headers,
        cache: "no-store",
      }),
      fetch(`${baseUrl}/tenants/${tenantId}/signals`, {
        headers,
        cache: "no-store",
      }),
      fetch(`${baseUrl}/tenants/${tenantId}/market/weather`, {
        headers,
        cache: "no-store",
      }),
    ]);

  if (!subscriptionResponse.ok || !signalsResponse.ok || !weatherResponse.ok) {
    throw new ApiClientError(
      "Zulu API returned an unavailable platform state.",
    );
  }

  throw new ApiClientError(
    "API aggregation is not enabled yet; use explicit fixture mode for local UI development.",
  );
}
