from dataclasses import dataclass

@dataclass
class CreativeRequest:
    purpose: str
    estimated_credits: float
    free_generation_available: bool = False
    explicit_approval: bool = False
    max_budget_credits: float = 0.0

@dataclass
class CreativeDecision:
    allowed: bool
    mode: str
    reason: str
    spend_credits: float

class HiggsfieldCreativeAdapter:
    def preflight(self, *, estimated_credits: float, free_generation_available: bool, max_budget_credits: float):
        if estimated_credits < 0:
            return CreativeDecision(False, "BLOCKED", "Invalid negative cost.", 0)
        if free_generation_available:
            return CreativeDecision(True, "FREE_CANDIDATE", "Free generation available; approval still required.", 0)
        if estimated_credits > max_budget_credits:
            return CreativeDecision(False, "BLOCKED", "Estimated cost exceeds budget.", 0)
        return CreativeDecision(True, "PAID_CANDIDATE", "Within budget; approval still required.", estimated_credits)

    def authorize(self, req: CreativeRequest):
        pre = self.preflight(
            estimated_credits=req.estimated_credits,
            free_generation_available=req.free_generation_available,
            max_budget_credits=req.max_budget_credits,
        )
        if not pre.allowed:
            return pre
        if not req.explicit_approval:
            return CreativeDecision(False, "BLOCKED", "Explicit approval required.", 0)
        if req.free_generation_available:
            return CreativeDecision(True, "FREE_APPROVED", "Approved free generation.", 0)
        return CreativeDecision(True, "PAID_APPROVED", "Approved paid generation.", req.estimated_credits)
