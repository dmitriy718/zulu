import { AppShell } from "../../components/AppShell";
import { LearningLabView } from "../../components/PageViews";
import { loadRouteContext } from "../../lib/routeGuards";

export default async function LearningLabPage() {
  const { data } = await loadRouteContext("signal_station");

  return (
    <AppShell data={data} active="Learning Lab">
      <LearningLabView data={data} />
    </AppShell>
  );
}
