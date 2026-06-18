import { AppShell } from "../components/AppShell";
import { CommandCenter } from "../components/CommandCenter";
import { loadRouteContext } from "../lib/routeGuards";

export default async function CommandCenterPage() {
  const { data } = await loadRouteContext();

  return (
    <AppShell data={data} active="Command Center">
      <CommandCenter data={data} />
    </AppShell>
  );
}
