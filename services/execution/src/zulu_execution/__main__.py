from zulu_execution import service_health


def main() -> None:
    print(service_health().model_dump_json())


if __name__ == "__main__":
    main()
