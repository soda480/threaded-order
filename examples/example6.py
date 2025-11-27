import json
from time import sleep
from threaded_order import Scheduler

s = Scheduler(workers=3, state={})

def json_safe_state(state):
    safe = {}
    for k, v in state.items():
        if k == "_state_lock":
            continue
        safe[k] = v
    return safe

@s.dregister(with_state=True)
def load(state):
    with state['_state_lock']:
        state['counter'] = state.get('counter', 0) + 1
    state["x"] = 10; return "loaded"

@s.dregister(with_state=True)
def behave(state):
    with state['_state_lock']:
        state['counter'] = state.get('counter', 0) + 1
    sleep(3); return "behaved"

@s.dregister(after=["load"], with_state=True)
def compute(state):
    with state['_state_lock']:
        state['counter'] = state.get('counter', 0) + 1
    state["x"] += 5; return state["x"]

s.start()
print(json.dumps(json_safe_state(s.state), indent=2))