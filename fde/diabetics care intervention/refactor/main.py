import math
import time
from collections import deque
from threading import Lock
from fastapi import Depends, FastAPI, HTTPException, Path, Query, Request, status

from models import (
    CareIntervention,
    CareInterventionUpdate,
    CareQueueItem,
    Encounter,
    ManagementDashboard,
    OperationsSummary,
    ReadmissionAnalysis,
)
from service import (
    get_all_encounters,
    get_care_intervention,
    get_care_queue,
    get_management_dashboard,
    get_operations_summary,
    get_readmission_analysis,
    update_care_intervention,
)


app = FastAPI(title="Patient Encounters API")
RATE_LIMIT = 60
RATE_WINDOW_SECONDS = 60
ENCOUNTERS_PAGE_SIZE = 50
CARE_QUEUE_PAGE_SIZE = 50
request_times: dict[str, deque[float]] = {}
request_times_lock = Lock()


def enforce_encounters_rate_limit(request: Request) -> None:
    client = request.client
    client_key = client.host if client is not None else "unknown"
    now = time.monotonic()
    cutoff = now - RATE_WINDOW_SECONDS

    with request_times_lock:
        timestamps = request_times.setdefault(client_key, deque())
        while timestamps and timestamps[0] <= cutoff:
            timestamps.popleft()

        if len(timestamps) >= RATE_LIMIT:
            retry_after = max(
                1, math.ceil(timestamps[0] + RATE_WINDOW_SECONDS - now)
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Try again later.",
                headers={"Retry-After": str(retry_after)},
            )

        timestamps.append(now)


@app.get("/encounters", response_model=list[Encounter])
def read_encounters(
    _: None = Depends(enforce_encounters_rate_limit),
    page: int = Query(
        default=1,
        ge=1,
        description="Page number (50 encounters per page)",
    ),
) -> list[Encounter]:
    return [
        Encounter.model_validate(row)
        for row in get_all_encounters(page, ENCOUNTERS_PAGE_SIZE)
    ]


@app.get("/encounters/{encounter_id}", response_model=CareIntervention)
def read_encounter(
    encounter_id: int = Path(gt=0),
    _: None = Depends(enforce_encounters_rate_limit),
) -> CareIntervention:
    intervention = get_care_intervention(encounter_id)
    if intervention is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No care intervention found for encounter {encounter_id}",
        )
    return CareIntervention.model_validate(intervention)


@app.get("/care-queue", response_model=list[CareQueueItem])
def read_care_queue(
    _: None = Depends(enforce_encounters_rate_limit),
    page: int = Query(
        default=1,
        ge=1,
        description="Page number (50 queue records per page)",
    ),
) -> list[CareQueueItem]:
    return [
        CareQueueItem.model_validate(row)
        for row in get_care_queue(
            ["MEDIUM", "HIGH"],
            page,
            CARE_QUEUE_PAGE_SIZE,
            "PENDING_REVIEW",
        )
    ]


@app.get("/care-queue/high", response_model=list[CareQueueItem])
def read_high_risk_care_queue(
    _: None = Depends(enforce_encounters_rate_limit),
    page: int = Query(
        default=1,
        ge=1,
        description="Page number (50 queue records per page)",
    ),
) -> list[CareQueueItem]:
    return [
        CareQueueItem.model_validate(row)
        for row in get_care_queue(["HIGH"], page, CARE_QUEUE_PAGE_SIZE)
    ]


@app.get("/operations/summary", response_model=OperationsSummary)
def read_operations_summary(
    _: None = Depends(enforce_encounters_rate_limit),
) -> OperationsSummary:
    return OperationsSummary.model_validate(get_operations_summary())


@app.get("/operations/readmission-analysis", response_model=ReadmissionAnalysis)
def read_readmission_analysis(
    _: None = Depends(enforce_encounters_rate_limit),
) -> ReadmissionAnalysis:
    return ReadmissionAnalysis.model_validate(get_readmission_analysis())


@app.get("/management/dashboard", response_model=ManagementDashboard)
def read_management_dashboard(
    _: None = Depends(enforce_encounters_rate_limit),
) -> ManagementDashboard:
    return ManagementDashboard.model_validate(get_management_dashboard())


@app.patch(
    "/interventions/{encounter_id}",
    response_model=CareIntervention,
)
def patch_care_intervention(
    encounter_id: int = Path(gt=0),
    intervention_update: CareInterventionUpdate = ...,
) -> CareIntervention:
    updated_intervention = update_care_intervention(
        encounter_id=encounter_id,
        status=intervention_update.status,
        assigned_to=intervention_update.assigned_to,
        notes=intervention_update.notes,
    )
    if updated_intervention is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No care intervention found for encounter {encounter_id}",
        )
    return CareIntervention.model_validate(updated_intervention)
