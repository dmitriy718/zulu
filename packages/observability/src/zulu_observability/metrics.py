from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

REQUIRED_METRICS = frozenset(
    {
        "api.health",
        "api.latency_ms",
        "queue.depth",
        "signals.throughput",
        "signals.rejected",
        "policy.blocks",
        "risk.blocks",
        "broker.errors",
        "reconciliation.discrepancies",
        "provider.rate_limits",
        "model.status",
        "incidents.active",
    }
)


@dataclass(frozen=True)
class MetricSample:
    name: str
    value: Decimal
    labels: dict[str, str] = field(default_factory=dict)


class ZuluMetrics:
    def __init__(self) -> None:
        self.samples: list[MetricSample] = []

    def record(self, name: str, value: Decimal | int | str, **labels: str) -> MetricSample:
        if name not in REQUIRED_METRICS:
            raise ValueError(f"unsupported metric: {name}")
        safe_labels = {
            key: value
            for key, value in labels.items()
            if key.lower() not in {"token", "credential", "api_key", "account_id"}
        }
        sample = MetricSample(name=name, value=Decimal(str(value)), labels=safe_labels)
        self.samples.append(sample)
        return sample

    def required_metric_names(self) -> frozenset[str]:
        return REQUIRED_METRICS
