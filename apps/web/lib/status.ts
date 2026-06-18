export type ServiceStatus = "healthy" | "starting" | "offline";

export interface StatusItem {
  name: string;
  status: ServiceStatus;
  detail: string;
}

export interface PlatformStatus {
  mode: "local" | "staging" | "production";
  liveTradingEnabled: boolean;
  services: StatusItem[];
}

export const localPlatformStatus: PlatformStatus = {
  mode: "local",
  liveTradingEnabled: false,
  services: [
    {
      name: "API",
      status: "healthy",
      detail: "Health and readiness endpoints are available.",
    },
    {
      name: "Signal Intelligence",
      status: "starting",
      detail: "Package is importable; market data adapters are not configured.",
    },
    {
      name: "Execution",
      status: "starting",
      detail: "Paper adapter boundary is present; live trading is disabled.",
    },
    {
      name: "Learning",
      status: "starting",
      detail: "Evaluation contracts are present; no model is promoted.",
    },
  ],
};

export function summarizeStatus(status: PlatformStatus): string {
  const healthyCount = status.services.filter(
    (service) => service.status === "healthy",
  ).length;
  return `${healthyCount}/${status.services.length} services healthy`;
}
