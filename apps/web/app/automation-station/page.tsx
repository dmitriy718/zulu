import { AppShell } from "../../components/AppShell";
import { AutomationStationView } from "../../components/PageViews";
import { loadRouteContext } from "../../lib/routeGuards";

export default async function AutomationStationPage() {
  const { data } = await loadRouteContext("automation_station");

  return (
    <AppShell data={data} active="Automation Station">
      <AutomationStationView data={data} />
    </AppShell>
  );
}
