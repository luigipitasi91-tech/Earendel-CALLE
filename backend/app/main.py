from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from .models import (
    GoalContract, ConsentLedger, EvidenceItem, EvidenceClass, Requirement
)
from .guardian import evaluate_before_call
from .verify import verify_goal
from .telephony import readiness, twilio_trial_capabilities
from .higgsfield_adapter import HiggsfieldCreativeAdapter, CreativeRequest
from .calle_adapter import readiness as calle_readiness, create_and_wait as calle_create_and_wait, evidence_from_calle

app = FastAPI(title="Future Call AI", version="1.0.0")

allowed_origins = [x.strip() for x in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


class LiveCalleRequest(BaseModel):
    task_id: str
    phone: str
    region: str = "GB"
    locale: str = "en-GB"


class FeedbackRequest(BaseModel):
    task_id: str
    stars: int = Field(ge=1, le=5)
    comment: str = ""


def _normalize_contract(raw: dict) -> GoalContract:
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
                requirement_key=key, text=transcript,
                classification=cls, explicit=True
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
                requirement_key=key, text=transcript,
                classification=cls, explicit=True
            ))
        else:
            evidence.append(EvidenceItem(
                requirement_key=key, text=transcript,
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
        "call_e": calle_readiness().__dict__,
    }


@app.get("/telephony/readiness")
def telephony_readiness():
    return {
        "readiness": readiness().__dict__,
        "trial_capabilities": twilio_trial_capabilities(),
    }


@app.get("/calle/readiness")
def calle_provider_readiness():
    return calle_readiness().__dict__


@app.post("/guardian/check")
def guardian_check(contract: GoalContract, consent: ConsentLedger):
    d = evaluate_before_call(contract, consent)
    return {"allowed": d.allowed, "reason": d.reason}


@app.post("/verify")
def verify(contract: GoalContract, evidence: list[EvidenceItem], call_completed: bool = True):
    return verify_goal(contract, evidence, call_completed)


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


def _ledger(consent: dict) -> ConsentLedger:
    return ConsentLedger(
        approved=consent["approved"],
        revoked=False,
        recipient=consent["recipient"],
        purpose=consent["purpose"],
        allowed_data=consent["allowed_data"],
        forbidden_actions=consent["forbidden_actions"],
        hard_constraints=consent["constraints"],
    )


@app.post("/calls/simulate")
def simulate_call(req: SimulateCall):
    task = TASKS.get(req.task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    consent = CONSENTS.get(req.task_id)
    if not consent or not consent.get("approved"):
        raise HTTPException(403, "Explicit consent required")

    contract = task["contract"]
    decision = evaluate_before_call(contract, _ledger(consent))
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


@app.post("/calls/calle/live")
def calle_live_call(req: LiveCalleRequest):
    task = TASKS.get(req.task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    consent = CONSENTS.get(req.task_id)
    if not consent or not consent.get("approved"):
        raise HTTPException(403, "Explicit consent required")

    contract = task["contract"]
    decision = evaluate_before_call(contract, _ledger(consent))
    if not decision.allowed:
        raise HTTPException(403, decision.reason)
    if not calle_readiness().configured:
        raise HTTPException(503, "CALL-E is not configured")

    provider = calle_create_and_wait(
        task=task["intent"],
        phone=req.phone,
        requirements=contract.success_conditions,
        metadata={"earendel_task_id": req.task_id},
        region=req.region,
        locale=req.locale,
    )
    completed = provider.get("status") == "completed"
    evidence = evidence_from_calle(provider, contract.success_conditions)
    result = verify_goal(contract, evidence, call_completed=completed)
    return {
        "mode": "LIVE_CALL_E",
        "provider_state": provider.get("status"),
        "provider_task_completed": provider.get("task_completed"),
        "goal_state": result.state.value,
        "verified": result.verified,
        "missing": result.missing,
        "contradicted": result.contradicted,
        "reason": result.reason,
        "provider_evidence": provider.get("evidence", []),
        "call_id": provider.get("id"),
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
