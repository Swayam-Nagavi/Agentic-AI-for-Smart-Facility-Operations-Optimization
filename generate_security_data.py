from pathlib import Path

from src.security_data_generator import (
    generate_security_events,
    save_security_events,
)


OUTPUT_FILE = Path("security_events.csv")


def main():
    rows = generate_security_events()
    output_file = save_security_events(rows, OUTPUT_FILE)

    print(f"Generated {len(rows)} security event CSV rows.")
    print(f"Created: {output_file.resolve()}")
    print("The dashboard will display only rows written to security_events.csv.")


if __name__ == "__main__":
    main()
