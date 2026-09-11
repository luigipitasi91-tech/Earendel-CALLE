from fastapi import FastAPI, HTTPException
import uuid
from pydantic import BaseModel, Field
from typing import Dict, Any
from .models import (
    GoalContract, ConsentLedger, EvidenceItem, EvidenceClass, Requirement
)
from .guardian import evaluate_before_call
from .verify import verify_goal
from .telephony import readiness, twilio_trial_capabilities
from .higgsfield_adapter import HiggsfieldCreativeAdapter, CreativeRequest

app = FastAPI(title="Future Call AI", version="1.0.0")

TASKS: Dict[str, Dict[str, Any]] = {}
CONSENTS: Dict[str, Dict[str, Any]] = {}
FEEDBACK: list[Dict[str, Any]] = []


class CreateTask(BaseModel):
    intent: str
    recipient: str
    contract: dict


class ConsentRequest(BaseModel):
    task_id: str
    recipient: str
    purpose: str
    allowed_data: list[str] = []
    forbidden_actions: list[str] = []
    constraints: list[str] = []
    approved: bool = False


class SimulateCall(BaseModel):
    task_id: str
    transcript: str


class FeedbackRequest(BaseModel):
    task_id: str
    stars: int = Field(ge=1, le=5)
    comment: str = ""


def _normalize_contract(raw: dict) -> GoalContract:
    # Supports both current schema and the original V1 schema.
    if "objective" in raw:
        return GoalContract(**raw)

    reqs = []
    for item in raw.get("success_requirements", []):
        reqs.append(
            Requirement(
                key=item.get("id") or item.get("key") or "requirement",
                description=item.get("text") or item.get("description") or "",
                required=True,
            )
        )
    return GoalContract(
        objective=raw.get("goal", ""),
        preferred=raw.get("preferred"),
        hard_constraints=raw.get("hard_constraints", []),
        allowed_data=raw.get("allowed_data", []),
        forbidden_actions=raw.get("forbidden_actions", []),
        success_conditions=reqs,
    )


def _classify_transcript(contract: GoalContract, transcript: str) -> list[EvidenceItem]:
    """
    Deterministic demo classifier for the appointment vertical slice.
    This is deliberately conservative: absence is neutral, not contradiction.
    """
    t = transcript.lower()
    evidence = []

    for req in contract.success_conditions:
        key = req.key
        desc = req.description.lower()

        if key in {"appointment", "date"} or "friday" in desc or "appointment" in desc:
            if any(p in t for p in [
                "cannot move", "can't move", "friday is unavailable",
                "friday unavailable", "remains on monday", "fully booked"
            ]):
                cls = EvidenceClass.CONTRADICTING
            elif "friday" in t and any(p in t for p in [
                "appointment is now", "appointment is rescheduled",
                "rescheduled to friday", "moved to friday", "friday at"
            ]):
                cls = EvidenceClass.SUPPORTING
            else:
                cls = EvidenceClass.NEUTRAL_OR_INSUFFICIENT
            evidence.append(EvidenceItem(
                requirement_key=key,
                text=transcript,
                classification=cls,
                explicit=True
            ))

        elif key == "fee" or "charge" in desc or "fee" in desc:
            if any(p in t for p in [
                "£20", "$20", "£25", "$25", "additional fee",
                "additional charge of", "rescheduling charge", "there will be a fee"
            ]):
                cls = EvidenceClass.CONTRADICTING
            elif any(p in t for p in [
                "no additional charge", "no extra charge",
                "there is no fee", "no rescheduling fee"
            ]):
                cls = EvidenceClass.SUPPORTING
            else:
                cls = EvidenceClass.NEUTRAL_OR_INSUFFICIENT
            evidence.append(EvidenceItem(
                requirement_key=key,
                text=transcript,
                classification=cls,
                explicit=True
            ))
        else:
            evidence.append(EvidenceItem(
                requirement_key=key,
                text=transcript,
                classification=EvidenceClass.NEUTRAL_OR_INSUFFICIENT,
                explicit=True
            ))
    return evidence


@app.get("/health")
def health():
    return {
        "status": "ok",
        "product": "Future Call AI",
        "epistemic_rule": "CALL_COMPLETED != TASK_COMPLETED",
        "telephony": readiness().__dict__,
    }


@app.get("/telephony/readiness")
def telephony_readiness():
    return {
        "readiness": readiness().__dict__,
        "trial_capabilities": twilio_trial_capabilities(),
    }


@app.post("/guardian/check")
def guardian_check(contract: GoalContract, consent: ConsentLedger):
    d = evaluate_before_call(contract, consent)
    return {"allowed": d.allowed, "reason": d.reason}


@app.post("/verify")
def verify(contract: GoalContract, evidence: list[EvidenceItem], call_completed: bool = True):
    return verify_goal(contract, evidence, call_completed)


# Backward-compatible V1 task flow used by existing tests and demo integrations.
@app.post("/tasks")
def create_task(req: CreateTask):
    task_id = str(uuid.uuid4())
    TASKS[task_id] = {
        "intent": req.intent,
        "recipient": req.recipient,
        "contract": _normalize_contract(req.contract),
    }
    return {"task_id": task_id, "status": "CREATED"}


@app.post("/consent")
def record_consent(req: ConsentRequest):
    if req.task_id not in TASKS:
        raise HTTPException(404, "Task not found")
    CONSENTS[req.task_id] = {
        "approved": req.approved,
        "recipient": req.recipient,
        "purpose": req.purpose,
        "allowed_data": req.allowed_data,
        "forbidden_actions": req.forbidden_actions,
        "constraints": req.constraints,
    }
    return {"task_id": req.task_id, "approved": req.approved}


@app.post("/calls/simulate")
def simulate_call(req: SimulateCall):
    task = TASKS.get(req.task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    consent = CONSENTS.get(req.task_id)
    if not consent or not consent.get("approved"):
        raise HTTPException(403, "Explicit consent required")

    contract = task["contract"]
    ledger = ConsentLedger(
        approved=consent["approved"],
        revoked=False,
        recipient=consent["recipient"],
        purpose=consent["purpose"],
        allowed_data=consent["allowed_data"],
        forbidden_actions=consent["forbidden_actions"],
        hard_constraints=consent["constraints"],
    )
    decision = evaluate_before_call(contract, ledger)
    if not decision.allowed:
        raise HTTPException(403, decision.reason)

    evidence = _classify_transcript(contract, req.transcript)
    result = verify_goal(contract, evidence, call_completed=True)
    return {
        "mode": "SIMULATED",
        "provider_state": "COMPLETED",
        "goal_state": result.state.value,
        "verified": result.verified,
        "missing": result.missing,
        "contradicted": result.contradicted,
        "reason": result.reason,
    }


@app.post("/feedback")
def feedback(req: FeedbackRequest):
    if req.task_id not in TASKS:
        raise HTTPException(404, "Task not found")
    item = req.model_dump()
    FEEDBACK.append(item)
    return {"accepted": True, **item}


creative_adapter = HiggsfieldCreativeAdapter()

@app.get("/creative/higgsfield/readiness")
def higgsfield_readiness():
    return {
        "status": "OPTIONAL",
        "core_dependency": False,
        "default_mode": "READ_ONLY",
        "cost_preflight_required": True,
        "generation_requires_explicit_approval": True,
    }

@app.post("/creative/higgsfield/authorize")
def higgsfield_authorize(req: CreativeRequest):
    return creative_adapter.authorize(req).__dict__
