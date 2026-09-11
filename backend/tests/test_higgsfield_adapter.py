from app.higgsfield_adapter import HiggsfieldCreativeAdapter, CreativeRequest
a = HiggsfieldCreativeAdapter()

def test_free_candidate_cost_zero():
    d = a.preflight(estimated_credits=12, free_generation_available=True, max_budget_credits=0)
    assert d.allowed and d.mode == "FREE_CANDIDATE" and d.spend_credits == 0

def test_no_approval_blocks_paid():
    d = a.authorize(CreativeRequest("Trailer", 4, False, False, 5))
    assert not d.allowed and d.spend_credits == 0

def test_no_approval_blocks_free():
    d = a.authorize(CreativeRequest("Trailer", 20, True, False, 0))
    assert not d.allowed and d.spend_credits == 0

def test_approved_free_cost_zero():
    d = a.authorize(CreativeRequest("Trailer", 20, True, True, 0))
    assert d.allowed and d.mode == "FREE_APPROVED" and d.spend_credits == 0

def test_approved_paid_within_budget():
    d = a.authorize(CreativeRequest("Reel", 4, False, True, 5))
    assert d.allowed and d.mode == "PAID_APPROVED" and d.spend_credits == 4

def test_over_budget_blocks():
    d = a.authorize(CreativeRequest("Trailer", 11, False, True, 5))
    assert not d.allowed and d.mode == "BLOCKED" and d.spend_credits == 0

def test_negative_cost_blocks():
    d = a.preflight(estimated_credits=-1, free_generation_available=False, max_budget_credits=10)
    assert not d.allowed
