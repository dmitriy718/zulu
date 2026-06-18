import { AppShell } from "../../components/AppShell";
import { IncidentsControlsView } from "../../components/PageViews";
import { loadRouteContext } from "../../lib/routeGuards";

export default async function IncidentsControlsPage() {
  const { data } = await loadRouteContext("automation_station");

  return (
    <AppShell data={data} active="Incidents & Controls">
      <IncidentsControlsView data={data} />
    </AppShell>
  );
}
