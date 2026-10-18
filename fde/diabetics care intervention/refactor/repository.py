from typing import Any

from database import get_connection


ENCOUNTER_COLUMNS = (
    "encounter_id",
    "patient_nbr",
    "age",
    "time_in_hospital",
    "num_lab_procedures",
    "num_procedures",
    "admission_type_id",
    "discharge_disposition_id",
    "number_inpatient",
    "number_emergency",
    "number_outpatient",
    "num_medications",
    "readmitted",
    "risk_score",
    "risk_level",
)


def get_all_encounters(limit: int, offset: int) -> list[dict[str, Any]]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    encounter_id,
                    patient_nbr,
                    age,
                    time_in_hospital,
                    number_inpatient,
                    number_emergency,
                    number_outpatient,
                    num_medications,
                    readmitted,
                    risk_score,
                    risk_level
                FROM patient_encounters
                ORDER BY encounter_id
                LIMIT %s OFFSET %s
                """,
                (limit, offset),
            )
            return cur.fetchall()


def get_care_intervention(encounter_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    intervention_id,
                    encounter_id,
                    status,
                    assigned_to,
                    notes
                FROM care_interventions
                WHERE encounter_id = %s
                """,
                (encounter_id,),
            )
            return cur.fetchone()


def get_care_queue(
    risk_levels: list[str],
    limit: int,
    offset: int,
    status: str | None = None,
) -> list[dict[str, Any]]:
    status_clause = "AND intervention.status = %s" if status is not None else ""
    params = (
        (risk_levels, status, limit, offset)
        if status is not None
        else (risk_levels, limit, offset)
    )
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    encounter.encounter_id,
                    encounter.patient_nbr,
                    encounter.age,
                    encounter.time_in_hospital,
                    encounter.number_inpatient,
                    encounter.number_emergency,
                    encounter.number_outpatient,
                    encounter.num_medications,
                    encounter.readmitted,
                    encounter.risk_score,
                    encounter.risk_level,
                    intervention.intervention_id,
                    intervention.status,
                    intervention.assigned_to,
                    intervention.notes
                FROM patient_encounters AS encounter
                JOIN care_interventions AS intervention
                    ON intervention.encounter_id = encounter.encounter_id
                WHERE encounter.risk_level = ANY(%s)
                    {status_clause}
                ORDER BY
                    CASE encounter.risk_level WHEN 'HIGH' THEN 0 ELSE 1 END,
                    encounter.risk_score DESC,
                    encounter.encounter_id
                LIMIT %s OFFSET %s
                """,
                params,
            )
            return cur.fetchall()


def get_operations_counts() -> dict[str, int]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    encounters.total_encounters,
                    encounters.high_risk,
                    encounters.medium_risk,
                    encounters.low_risk,
                    interventions.pending_interventions,
                    interventions.completed_interventions
                FROM (
                    SELECT
                        COUNT(*) AS total_encounters,
                        COUNT(*) FILTER (WHERE risk_level = 'HIGH') AS high_risk,
                        COUNT(*) FILTER (WHERE risk_level = 'MEDIUM') AS medium_risk,
                        COUNT(*) FILTER (WHERE risk_level = 'LOW') AS low_risk
                    FROM patient_encounters
                ) AS encounters
                CROSS JOIN (
                    SELECT
                        COUNT(*) FILTER (WHERE status = 'PENDING_REVIEW')
                            AS pending_interventions,
                        COUNT(*) FILTER (WHERE status = 'CLOSED')
                            AS completed_interventions
                    FROM care_interventions
                ) AS interventions
                """
            )
            return cur.fetchone()


def get_high_risk_readmission_counts() -> dict[str, int]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*) AS high_risk_patients,
                    COUNT(*) FILTER (WHERE readmitted = '<30')
                        AS high_risk_readmitted_under_30_days
                FROM patient_encounters
                WHERE risk_level = 'HIGH'
                """
            )
            return cur.fetchone()


def get_management_dashboard_counts() -> dict[str, int]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    encounters.total_diabetes_encounters,
                    encounters.readmitted_under_30_days,
                    encounters.high_risk_population,
                    encounters.high_risk_30_day_readmissions,
                    interventions.care_queue_pending
                FROM (
                    SELECT
                        COUNT(*) AS total_diabetes_encounters,
                        COUNT(*) FILTER (WHERE readmitted = '<30')
                            AS readmitted_under_30_days,
                        COUNT(*) FILTER (WHERE risk_level = 'HIGH')
                            AS high_risk_population,
                        COUNT(*) FILTER (
                            WHERE risk_level = 'HIGH' AND readmitted = '<30'
                        ) AS high_risk_30_day_readmissions
                    FROM patient_encounters
                ) AS encounters
                CROSS JOIN (
                    SELECT COUNT(*) FILTER (WHERE status = 'PENDING_REVIEW')
                        AS care_queue_pending
                    FROM care_interventions
                ) AS interventions
                """
            )
            return cur.fetchone()


def update_care_intervention(
    encounter_id: int,
    status: str,
    assigned_to: str | None,
    notes: str | None,
) -> dict[str, Any] | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE care_interventions AS intervention
                SET
                    status = %s,
                    assigned_to = %s,
                    notes = %s
                WHERE intervention_id = (
                    SELECT intervention_id
                    FROM care_interventions
                    WHERE encounter_id = %s
                    ORDER BY intervention_id DESC
                    LIMIT 1
                )
                RETURNING
                    intervention_id,
                    encounter_id,
                    status,
                    assigned_to,
                    notes
                """,
                (status, assigned_to, notes, encounter_id),
            )
            return cur.fetchone()


def import_encounter_batch(
    encounters: list[dict[str, Any]],
    intervention_encounter_ids: list[int],
) -> None:
    """Upsert encounters and create missing interventions in one transaction."""
    columns = ", ".join(ENCOUNTER_COLUMNS)
    placeholders = ", ".join(f"%({column})s" for column in ENCOUNTER_COLUMNS)
    updates = ", ".join(
        f"{column} = EXCLUDED.{column}"
        for column in ENCOUNTER_COLUMNS
        if column != "encounter_id"
    )
    upsert_sql = f"""
        INSERT INTO patient_encounters ({columns})
        VALUES ({placeholders})
        ON CONFLICT (encounter_id) DO UPDATE SET {updates}
    """
    intervention_sql = """
        INSERT INTO care_interventions (encounter_id, status, assigned_to, notes)
        VALUES (%s, 'PENDING_REVIEW', NULL, NULL)
        ON CONFLICT (encounter_id) DO NOTHING
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(upsert_sql, encounters)
            if intervention_encounter_ids:
                cur.executemany(
                    intervention_sql,
                    [(encounter_id,) for encounter_id in intervention_encounter_ids],
                )