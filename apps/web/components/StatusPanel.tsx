import type { PlatformStatus } from "../lib/status";
import { summarizeStatus } from "../lib/status";

export function StatusPanel({ status }: Readonly<{ status: PlatformStatus }>) {
  return (
    <section
      className="card system-status"
      aria-labelledby="system-status-title"
    >
      <span className="pill">{summarizeStatus(status)}</span>
      <h2 id="system-status-title">Local platform status</h2>
      <ul>
        {status.services.map((service) => (
          <li key={service.name}>
            <strong>{service.name}:</strong> {service.status}. {service.detail}
          </li>
        ))}
      </ul>
    </section>
  );
}
