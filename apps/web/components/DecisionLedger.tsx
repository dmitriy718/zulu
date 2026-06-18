import type { DecisionLedgerEntry } from "../lib/platform";
import { freshnessLabel } from "../lib/platform";

export function DecisionLedger({
  entries,
}: Readonly<{ entries: DecisionLedgerEntry[] }>) {
  return (
    <ol className="ledger-list" aria-label="Chronological decision ledger">
      {entries.map((entry) => (
        <li key={entry.id} className="ledger-entry">
          <div className="ledger-rail" aria-hidden="true" />
          <article>
            <header>
              <span>{entry.type}</span>
              <strong>{entry.status}</strong>
            </header>
            <h2>{entry.summary}</h2>
            <p>
              {entry.actor} / {freshnessLabel(entry.occurred_at)}
            </p>
            <ul>
              {entry.trace.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </article>
        </li>
      ))}
    </ol>
  );
}
