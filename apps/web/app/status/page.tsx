import { AppShell } from "../../components/AppShell";
import { StatusPanel } from "../../components/StatusPanel";
import { loadRouteContext } from "../../lib/routeGuards";
import { localPlatformStatus } from "../../lib/status";

export default async function StatusPage() {
  const { data } = await loadRouteContext();

  return (
    <AppShell data={data} active="Settings">
      <StatusPanel status={localPlatformStatus} />
    </AppShell>
  );
}
