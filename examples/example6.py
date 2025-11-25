import json
from time import sleep
from threaded_order import Scheduler

s = Scheduler(workers=3, state={})

@s.dregister(with_state=True)
def load(state):
    state["x"] = 10; return "loaded"

@s.dregister(with_state=True)
def behave(state):
    sleep(3); return "behaved"

@s.dregister(after=["load"], with_state=True)
def compute(state):
    state["x"] += 5; return state["x"]

s.start()
print(json.dumps(s.state, indent=2))