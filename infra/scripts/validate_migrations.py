from __future__ import annotations

import subprocess
import sys

from sqlalchemy import create_engine, inspect, text

EXPECTED_TABLES = {
    "audit_events",
    "broker_connections",
    "broker_order_requests",
    "clean_signals",
    "execution_intents",
    "feature_vectors",
    "headline_events",
    "market_data_snapshots",
    "market_weather_snapshots",
    "model_evaluation_reports",
    "model_manifests",
    "near_miss_labels",
    "option_contract_snapshots",
    "order_lifecycle_events",
    "outbox_events",
    "policy_decisions",
    "positions",
    "risk_decisions",
    "strategy_candidates",
    "subscriptions",
    "system_incidents",
    "tenants",
    "trade_outcomes",
    "user_override_events",
    "users",
}


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def main() -> int:
    database_url = "postgresql+psycopg://zulu:zulu_dev_password@localhost:5432/zulu"
    run(["uv", "run", "alembic", "-c", "infra/alembic.ini", "downgrade", "base"])
    run(["uv", "run", "alembic", "-c", "infra/alembic.ini", "upgrade", "head"])

    engine = create_engine(database_url)
    with engine.connect() as connection:
        tables = set(inspect(connection).get_table_names())
        missing = EXPECTED_TABLES - tables
        if missing:
            raise RuntimeError(f"missing migrated tables: {sorted(missing)}")
        audit_trigger = connection.execute(
            text("select count(*) from pg_trigger where tgname = 'audit_events_immutable'")
        ).scalar_one()
        signal_trigger = connection.execute(
            text("select count(*) from pg_trigger where tgname = 'clean_signal_guard'")
        ).scalar_one()
        if audit_trigger != 1 or signal_trigger != 1:
            raise RuntimeError("expected ledger triggers were not installed")

    run(["uv", "run", "alembic", "-c", "infra/alembic.ini", "downgrade", "base"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
