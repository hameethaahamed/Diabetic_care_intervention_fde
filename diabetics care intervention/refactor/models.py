from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, model_validator


class Encounter(BaseModel):
    encounter_id: int
    patient_nbr: int | None = None
    age: str | None = None
    time_in_hospital: int | None = None
    number_inpatient: int | None = None
    number_emergency: int | None = None
    number_outpatient: int | None = None
    num_medications: int | None = None
    readmitted: str | None = None
    risk_score: float | None = None
    risk_level: str | None = None


class CareQueueItem(Encounter):
    intervention_id: int
    status: str
    assigned_to: str | None = None
    notes: str | None = None


class CareIntervention(BaseModel):
    intervention_id: int
    encounter_id: int
    status: str
    assigned_to: str | None = None
    notes: str | None = None


class InterventionStatus(str, Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    ASSIGNED = "ASSIGNED"
    CONTACTED = "CONTACTED"
    FOLLOW_UP_SCHEDULED = "FOLLOW_UP_SCHEDULED"
    CLOSED = "CLOSED"

class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class Readmitted(str, Enum):
    UNDER_30 = "<30"
    OVER_30 = ">30"
    NO = "NO"

class HealthResponse(BaseModel):
    status: str

class InterventionUpdate(BaseModel):
    status: Optional[InterventionStatus] = None
    assigned_to: Optional[str] = Field(default=None, max_length=100)
    notes: Optional[str] = None

    @model_validator(mode="after")
    def require_one_field(self):
        if self.status is None and self.assigned_to is None and self.notes is None: raise ValueError("Provide at least one of: status, assigned_to, notes")
        return self


CareInterventionUpdate = InterventionUpdate


class OperationsSummary(BaseModel):
    total_encounters: int
    high_risk: int
    medium_risk: int
    low_risk: int
    pending_interventions: int
    completed_interventions: int

class ReadmissionAnalysis(BaseModel):
    high_risk_patients: int
    high_risk_readmitted_under_30_days: int
    high_risk_readmission_rate: float

class ManagementDashboard(BaseModel):
    total_diabetes_encounters: int
    readmitted_under_30_days: int
    readmission_rate: float
    high_risk_population: int
    high_risk_percent: float
    high_risk_30_day_readmissions: int
    care_queue_pending: int
