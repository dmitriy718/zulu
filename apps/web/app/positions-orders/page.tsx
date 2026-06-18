import { AppShell } from "../../components/AppShell";
import { PositionsOrdersView } from "../../components/PageViews";
import { loadRouteContext } from "../../lib/routeGuards";

export default async function PositionsOrdersPage() {
  const { data } = await loadRouteContext("automation_station");

  return (
    <AppShell data={data} active="Positions & Orders">
      <PositionsOrdersView data={data} />
    </AppShell>
  );
}
