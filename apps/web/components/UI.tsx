import {
  CheckCircle2,
  CircleDot,
  OctagonAlert,
  ShieldAlert,
} from "lucide-react";
import { clsx } from "clsx";

import type { ServiceState } from "../lib/platform";

const statusIcons = {
  ok: CheckCircle2,
  passed: CheckCircle2,
  review: CircleDot,
  active: CircleDot,
  degraded: ShieldAlert,
  blocked: OctagonAlert,
  offline: OctagonAlert,
} as const;

export function StatusBadge({
  status,
  children,
}: Readonly<{
  status: ServiceState | "passed" | "review" | "active";
  children: React.ReactNode;
}>) {
  const Icon = statusIcons[status];

  return (
    <span className={clsx("status-badge", `status-${status}`)}>
      <Icon aria-hidden="true" size={14} strokeWidth={2.2} />
      {children}
    </span>
  );
}

export function SectionHeader({
  eyebrow,
  title,
  description,
}: Readonly<{ eyebrow?: string; title: string; description?: string }>) {
  return (
    <div className="section-header">
      {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
      <h2>{title}</h2>
      {description ? <p>{description}</p> : null}
    </div>
  );
}

export function EmptyState({
  title,
  detail,
}: Readonly<{ title: string; detail: string }>) {
  return (
    <section className="empty-state" aria-live="polite">
      <h2>{title}</h2>
      <p>{detail}</p>
    </section>
  );
}

export function ErrorState({
  title,
  detail,
}: Readonly<{ title: string; detail: string }>) {
  return (
    <section className="error-state" role="alert">
      <h2>{title}</h2>
      <p>{detail}</p>
    </section>
  );
}
