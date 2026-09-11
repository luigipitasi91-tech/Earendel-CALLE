from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional, Dict


class GoalState(str, Enum):
    UNKNOWN = "UNKNOWN"
    ATTEMPTED = "ATTEMPTED"
    PARTIAL = "PARTIAL"
    VERIFIED_SUCCESS = "VERIFIED_SUCCESS"
    FAILED = "FAILED"


class EvidenceClass(str, Enum):
    SUPPORTING = "SUPPORTING"
    CONTRADICTING = "CONTRADICTING"
    NEUTRAL_OR_INSUFFICIENT = "NEUTRAL_OR_INSUFFICIENT"


class CallState(str, Enum):
    CREATED = "CREATED"
    INITIATED = "INITIATED"
    RINGING = "RINGING"
    ANSWERED = "ANSWERED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BUSY = "BUSY"
    NO_ANSWER = "NO_ANSWER"
    CANCELED = "CANCELED"


class Requirement(BaseModel):
    key: str
    description: str
    required: bool = True


class GoalContract(BaseModel):
    objective: str
    preferred: Optional[str] = None
    hard_constraints: List[str] = Field(default_factory=list)
    allowed_data: List[str] = Field(default_factory=list)
    forbidden_actions: List[str] = Field(default_factory=list)
    success_conditions: List[Requirement] = Field(default_factory=list)


class ConsentLedger(BaseModel):
    approved: bool = False
    revoked: bool = False
    recipient: str
    purpose: str
    allowed_data: List[str] = Field(default_factory=list)
    forbidden_actions: List[str] = Field(default_factory=list)
    hard_constraints: List[str] = Field(default_factory=list)


class EvidenceItem(BaseModel):
    requirement_key: str
    text: str
    source: str = "recipient_transcript"
    classification: EvidenceClass = EvidenceClass.NEUTRAL_OR_INSUFFICIENT
    explicit: bool = True
    sequence: int = 0


class VerificationResult(BaseModel):
    state: GoalState
    verified: List[str] = Field(default_factory=list)
    missing: List[str] = Field(default_factory=list)
    contradicted: List[str] = Field(default_factory=list)
    refutation_notes: List[str] = Field(default_factory=list)
    reason: str


class ProviderEvent(BaseModel):
    event_id: str
    sequence: int
    state: CallState
    payload: Dict = Field(default_factory=dict)
