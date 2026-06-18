import { AppShell } from "../../components/AppShell";
import { MarketWeatherView } from "../../components/PageViews";
import { loadRouteContext } from "../../lib/routeGuards";

export default async function MarketWeatherPage() {
  const { data } = await loadRouteContext("signal_station");

  return (
    <AppShell data={data} active="Market Weather">
      <MarketWeatherView data={data} />
    </AppShell>
  );
}
