import { AppShell } from "../../components/AppShell";
import { SignalStationView } from "../../components/PageViews";
import { loadRouteContext } from "../../lib/routeGuards";

export default async function SignalStationPage() {
  const { data } = await loadRouteContext("signal_station");

  return (
    <AppShell data={data} active="Signal Station">
      <SignalStationView data={data} />
    </AppShell>
  );
}
