[![ci](https://github.com/soda480/threaded-order/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/soda480/threaded-order/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/threaded-order.svg)](https://badge.fury.io/py/threaded-order)

# threaded-order
A lightweight Python framework for running functions concurrently across multiple threads while maintaining defined execution order. It lets you declare dependencies between tasks—so some run only after others complete—without complex orchestration code. 

Ideal for dependency-aware test execution, build pipelines, and automation workflows that benefit from controlled concurrency.

Key Features
* Concurrent task execution using Python threads
* Dependency graph automatically determines order
* Simple registration and decorator API
* Shared thread-safe state: tasks can opt in to receive a shared state dict and read/write values across dependent tasks
* Automatic result capture: each task’s return value is stored under `state['results'][task_name]`
* Thread-safe logging, callbacks, and run summary
* Graceful shutdown on interrupt

## Installation

```
pip install threaded-order
```

### Simple Example

![graph](https://github.com/soda480/threaded-order/blob/main/docs/images/graph.png?raw=true)

```Python
from threaded_order import Scheduler, ThreadProxyLogger
import time
import random

s = Scheduler(workers=3, setup_logging=True)
logger = ThreadProxyLogger()

def run(name):
    time.sleep(random.uniform(.5, 3.5))
    logger.info(f'{name} completed')

@s.dregister()
def a(): run('a')

@s.dregister(after=['a'])
def b(): run('b')

@s.dregister(after=['a'])
def c(): run('c')

@s.dregister(after=['c'])
def d(): run('d')

@s.dregister(after=['c'])
def e(): run('e')

@s.dregister(after=['b', 'd'])
def f(): run('f')

if __name__ == '__main__':
    s.on_scheduler_done(lambda s: print(f"Passed:{len(s['passed'])} Failed:{len(s['failed'])}"))
    s.start()
```

![example4](https://github.com/soda480/threaded-order/blob/main/docs/images/example4.gif?raw=true)

### Shared State Example

```Python
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
```

Output:
```
{
  "results": {
    "load": "loaded",
    "compute": 15,
    "behave": "behaved"
  },
  "x": 15
}
```

### ProgressBar Integration Example

Can be done by using the `on_task_done` callback. See [example5](https://github.com/soda480/threaded-order/blob/main/examples/example5.py)

![example5](https://github.com/soda480/threaded-order/blob/main/docs/images/example5.gif?raw=true)


See examples in examples folder. To run examples, follow instructions below to build and run the Docker container then execute:

## API Overview
`class Scheduler(workers=None, setup_logging=False, add_stream_handler=True)`

Runs registered callables across multiple threads while respecting declared dependencies.

### Core Methods
| Method | Description |
| --- | --- |
| `register(obj, name, after=None)` |	Register a callable for execution. after defines dependencies by name. |
| `dregister(after=None)` |	Decorator variant of register() for inline task definitions. |
| `start()` |	Start execution, respecting dependencies. Returns a summary dictionary. |

### Callbacks

All are optional and run on the scheduler thread (never worker threads).

| Callback | When Fired | Signature |
| --- | --- | --- |
| `on_task_start(fn)`      | Before a task starts | (name) |
| `on_task_run(fn)`        | When tasks starts running on a thread | (name, thread) |
| `on_task_done(fn)`       | After a task finishes | (name, ok) |
| `on_scheduler_start(fn)` | Before scheduler starts running tasks | (meta) |
| `on_scheduler_done(fn)`  | After all tasks complete | (summary) |

### Interrupt Handling

Press Ctrl-C during execution to gracefully cancel outstanding work:
* Running tasks finish naturally or are marked as cancelled
* Remaining queued tasks are discarded
* Final summary reflects all results

## Development

Clone the repository and ensure the latest version of Docker is installed on your development server.

Build the Docker image:
```sh
docker image build \
-t threaded-order:latest .
```

Run the Docker container:
```sh
docker container run \
--rm \
-it \
-v $PWD:/code \
threaded-order:latest \
bash
```

Execute the dev pipeline:
```sh
make dev
```
