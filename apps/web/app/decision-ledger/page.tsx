import { AppShell } from "../../components/AppShell";
import { DecisionLedger } from "../../components/DecisionLedger";
import { SectionHeader } from "../../components/UI";
import { loadRouteContext } from "../../lib/routeGuards";

export default async function DecisionLedgerPage() {
  const { data } = await loadRouteContext("signal_station");

  return (
    <AppShell data={data} active="Decision Ledger">
      <div className="page-stack">
        <SectionHeader
          eyebrow="Decision Ledger"
          title="Chronological audit and decision trace"
          description="Accepted, rejected, expired, executed, policy, risk, broker, override, and audit events stay visible."
        />
        <DecisionLedger entries={data.ledger} />
      </div>
    </AppShell>
  );
}
