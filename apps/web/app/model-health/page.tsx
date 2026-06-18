import { AppShell } from "../../components/AppShell";
import { ModelHealthView } from "../../components/PageViews";
import { loadRouteContext } from "../../lib/routeGuards";

export default async function ModelHealthPage() {
  const { data } = await loadRouteContext("signal_station");

  return (
    <AppShell data={data} active="Model Health">
      <ModelHealthView data={data} />
    </AppShell>
  );
}
