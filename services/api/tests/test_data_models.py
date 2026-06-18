from zulu_api.data import Base


def test_domain_tables_are_registered_in_metadata() -> None:
    expected_tables = {
        "audit_events",
        "broker_order_requests",
        "clean_signals",
        "market_data_snapshots",
        "option_contract_snapshots",
        "outbox_events",
        "tenants",
    }

    assert expected_tables.issubset(Base.metadata.tables.keys())
