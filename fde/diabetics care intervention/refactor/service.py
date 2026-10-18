import csv
from pathlib import Path
from typing import Any, TypedDict

from repository import (
    get_all_encounters as repository_get_all_encounters,
    get_care_queue as repository_get_care_queue,
    get_care_intervention as repository_get_care_intervention,
    get_high_risk_readmission_counts as repository_get_high_risk_readmission_counts,
    get_management_dashboard_counts as repository_get_management_dashboard_counts,
    get_operations_counts as repository_get_operations_counts,
    import_encounter_batch,
    update_care_intervention as repository_update_care_intervention,
)


BATCH_SIZE = 1_000
REQUIRED_COLUMNS = (
    "encounter_id",
    "patient_nbr",
    "age",
    "time_in_hospital",
    "number_inpatient",
    "number_emergency",
    "number_outpatient",
    "num_medications",
    "readmitted",
)
NULL_LIKE_VALUES = {"", "?", "NULL", "NA", "N/A", "NAN"}


class EncounterRecord(TypedDict):
    encounter_id: int
    patient_nbr: int
    age: str | None
    time_in_hospital: int | None
    number_inpatient: int | None
    number_emergency: int | None
    number_outpatient: int | None
    num_medications: int | None
    num_lab_procedures: int | None
    num_procedures: int | None
    admission_type_id: int | None
    discharge_disposition_id: int | None
    readmitted: str | None
    risk_score: int
    risk_level: str


def calculate_risk(encounter: dict[str, int | None]) -> tuple[int, str]:
    """Score from utilization and treatment factors, never the historical outcome."""
    number_inpatient = encounter.get("number_inpatient") or 0
    number_emergency = encounter.get("number_emergency") or 0
    number_outpatient = encounter.get("number_outpatient") or 0
    time_in_hospital = encounter.get("time_in_hospital") or 0
    num_medications = encounter.get("num_medications") or 0
    risk_score = (
        (3 if number_inpatient >= 3 else 0)
        + (2 if number_emergency >= 2 else 0)
        + (1 if number_outpatient >= 3 else 0)
        + (1 if time_in_hospital >= 7 else 0)
        + (1 if num_medications >= 20 else 0)
    )
    risk_level = (
        "LOW" if risk_score <= 2 else "MEDIUM" if risk_score <= 4 else "HIGH"
    )
    return risk_score, risk_level


def _required_value(row: dict[str, str | None], field: str) -> str:
    value = row.get(field)
    if value is None or value.strip().upper() in NULL_LIKE_VALUES:
        raise ValueError(f"CSV row is missing the {field!r} value")
    return value.strip()


def _optional_text(row: dict[str, str | None], field: str) -> str | None:
    value = row.get(field)
    if value is None or value.strip().upper() in NULL_LIKE_VALUES:
        return None
    return value.strip()


def _optional_integer(row: dict[str, str | None], field: str, line_number: int) -> int | None:
    value = _optional_text(row, field)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(
            f"Invalid patient data on CSV line {line_number}: "
            f"column {field!r} is not an integer: {value!r}"
        ) from exc


def _prepare_encounter(
    row: dict[str, str | None], line_number: int
) -> EncounterRecord:
    try:
        encounter_id = int(_required_value(row, "encounter_id"))
        patient_nbr = int(_required_value(row, "patient_nbr"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid patient data on CSV line {line_number}: {exc}") from exc

    risk_inputs = {
        field: _optional_integer(row, field, line_number)
        for field in (
            "time_in_hospital",
            "number_inpatient",
            "number_emergency",
            "number_outpatient",
            "num_medications",
        )
    }
    risk_score, risk_level = calculate_risk(risk_inputs)
    return {
        "encounter_id": encounter_id,
        "patient_nbr": patient_nbr,
        "age": _optional_text(row, "age"),
        **risk_inputs,
        "num_lab_procedures": _optional_integer(
            row, "num_lab_procedures", line_number
        ),
        "num_procedures": _optional_integer(row, "num_procedures", line_number),
        "admission_type_id": _optional_integer(row, "admission_type_id", line_number),
        "discharge_disposition_id": _optional_integer(
            row, "discharge_disposition_id", line_number
        ),
        "readmitted": _optional_text(row, "readmitted"),
        "risk_score": risk_score,
        "risk_level": risk_level,
    }


def import_dataset(path: Path) -> tuple[int, int]:
    """Import CSV encounters and queue MEDIUM/HIGH rows in batches."""
    processed_count = 0
    intervention_candidates = 0
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        missing = [
            column
            for column in REQUIRED_COLUMNS
            if column not in (reader.fieldnames or [])
        ]
        if missing:
            raise ValueError(f"CSV is missing required columns: {', '.join(missing)}")

        batch: list[EncounterRecord] = []
        for line_number, row in enumerate(reader, start=2):
            batch.append(_prepare_encounter(row, line_number))
            if len(batch) >= BATCH_SIZE:
                processed, candidates = _flush_batch(batch)
                processed_count += processed
                intervention_candidates += candidates
                batch.clear()

        if batch:
            processed, candidates = _flush_batch(batch)
            processed_count += processed
            intervention_candidates += candidates

    if processed_count == 0:
        raise ValueError(f"No patient records found in {path}")
    return processed_count, intervention_candidates


def _flush_batch(batch: list[EncounterRecord]) -> tuple[int, int]:
    intervention_ids = [
        encounter["encounter_id"]
        for encounter in batch
        if encounter["risk_level"] in ("MEDIUM", "HIGH")
    ]
    import_encounter_batch(batch, intervention_ids)
    return len(batch), len(intervention_ids)


def get_all_encounters(page: int, page_size: int = 50) -> list[dict[str, Any]]:
    offset = (page - 1) * page_size
    return repository_get_all_encounters(limit=page_size, offset=offset)


def get_care_intervention(encounter_id: int) -> dict[str, Any] | None:
    return repository_get_care_intervention(encounter_id)


def get_care_queue(
    risk_levels: list[str],
    page: int,
    page_size: int = 50,
    status: str | None = None,
) -> list[dict[str, Any]]:
    offset = (page - 1) * page_size
    return repository_get_care_queue(
        risk_levels,
        limit=page_size,
        offset=offset,
        status=status,
    )


def get_operations_summary() -> dict[str, int]:
    return repository_get_operations_counts()


def get_readmission_analysis() -> dict[str, int | float]:
    counts = repository_get_high_risk_readmission_counts()
    high_risk_patients = counts["high_risk_patients"]
    readmitted_under_30_days = counts["high_risk_readmitted_under_30_days"]
    rate = (
        round(readmitted_under_30_days * 100 / high_risk_patients, 2)
        if high_risk_patients
        else 0.0
    )
    return {
        **counts,
        "high_risk_readmission_rate": rate,
    }


def get_management_dashboard() -> dict[str, int | float]:
    counts = repository_get_management_dashboard_counts()
    total_encounters = counts["total_diabetes_encounters"]
    readmitted_under_30_days = counts["readmitted_under_30_days"]
    high_risk_population = counts["high_risk_population"]
    return {
        **counts,
        "readmission_rate": (
            round(readmitted_under_30_days * 100 / total_encounters, 2)
            if total_encounters
            else 0.0
        ),
        "high_risk_percent": (
            round(high_risk_population * 100 / total_encounters, 2)
            if total_encounters
            else 0.0
        ),
    }


def update_care_intervention(
    encounter_id: int,
    status: str,
    assigned_to: str | None,
    notes: str | None,
) -> dict[str, Any] | None:
    return repository_update_care_intervention(encounter_id, status, assigned_to, notes)
