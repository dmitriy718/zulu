import { AppShell } from "../../components/AppShell";
import { SettingsView } from "../../components/PageViews";
import { loadRouteContext } from "../../lib/routeGuards";

export default async function SettingsPage() {
  const { data } = await loadRouteContext();

  return (
    <AppShell data={data} active="Settings">
      <SettingsView data={data} />
    </AppShell>
  );
}
