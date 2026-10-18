import argparse
from pathlib import Path

from service import import_dataset


CSV_PATH = Path(__file__).resolve().parents[1] / "data" / "diabetic_data.csv"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Clean, score, and import diabetes encounters and care interventions."
    )
    parser.add_argument(
        "csv_path",
        nargs="?",
        type=Path,
        default=CSV_PATH,
        help=f"CSV input path (default: {CSV_PATH})",
    )
    csv_path = parser.parse_args().csv_path
    processed_count, intervention_candidates = import_dataset(csv_path)
    print(f"Inserted or updated {processed_count} patient encounter records.")
    print(
        "MEDIUM/HIGH encounters considered for care interventions: "
        f"{intervention_candidates}"
    )


if __name__ == "__main__":
    main()
