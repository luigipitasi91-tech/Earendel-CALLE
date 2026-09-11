from .models import ProviderEvent, CallState

TERMINAL = {CallState.COMPLETED, CallState.FAILED, CallState.BUSY, CallState.NO_ANSWER, CallState.CANCELED}
RANK = {
    CallState.CREATED: 0,
    CallState.INITIATED: 1,
    CallState.RINGING: 2,
    CallState.ANSWERED: 3,
    CallState.COMPLETED: 4,
    CallState.FAILED: 4,
    CallState.BUSY: 4,
    CallState.NO_ANSWER: 4,
    CallState.CANCELED: 4,
}

class EventReducer:
    def __init__(self):
        self.state = CallState.CREATED
        self.seen_ids = set()
        self.last_sequence = -1

    def apply(self, event: ProviderEvent):
        if event.event_id in self.seen_ids:
            return self.state, "duplicate_ignored"
        self.seen_ids.add(event.event_id)

        if event.sequence < self.last_sequence:
            return self.state, "out_of_order_ignored"

        if self.state in TERMINAL:
            return self.state, "terminal_state_ignored"

        if RANK[event.state] < RANK[self.state]:
            return self.state, "regression_ignored"

        self.state = event.state
        self.last_sequence = max(self.last_sequence, event.sequence)
        return self.state, "applied"
