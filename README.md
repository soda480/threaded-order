[![ci](https://github.com/soda480/threaded-order/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/soda480/threaded-order/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/threaded-order.svg)](https://badge.fury.io/py/threaded-order)

# threaded-order
A lightweight Python framework for running functions across multiple threads while enforcing dependency-defined execution order. You declare task dependencies, and the scheduler handles both sequencing and concurrency.

Great for dependency-aware test runs, build pipelines, and automation flows that need structure without giving up speed.

Key Features
* Concurrent execution using Python threads, coordinated by a dependency graph
* Simple registration and decorator-based API
* Shared, thread-safe state (opt-in) with a built-in lock for safe cross-thread mutation
* Thread-safe logging, callbacks, and run summaries
* Graceful shutdown on interrupt
* A CLI runner that uses threaded-order’s DAG engine to run tests in parallel while preserving deterministic, dependency-aware ordering

## Installation

```
pip install threaded-order
```

## API Overview
```python
class Scheduler(
    workers=None, # maximum number of worker threads that can run tasks concurrently.
    state=None, # optional shared dictionary passed to tasks marked with with_state=True
    store_results=True, # automatically save task return values into state["results"]
    clear_results_on_start=True, # wipe state["results"] at the start of each run
    setup_logging=False, # enable built-in logging configuration for scheduler and worker threads.
    add_stream_handler=True, # attach a stream handler to the logger when logging is enabled.
    verbose=False # enable extra scheduler and task-level debug logging
) 
```

Runs registered callables across multiple threads while respecting declared dependencies.

### Core Methods
| Method | Description |
| --- | --- |
| `register(obj, name, after=None, with_state=False)` |	Register a callable for execution. after defines dependencies by name, specify if function is to receive the shared state. |
| `dregister(after=None, with_state=False)` | Decorator variant of register() for inline task definitions. |
| `start()` | Start execution, respecting dependencies. Returns a summary dictionary. |
| `dmark(after=None, with_state=False, tag=None)` | Decorator that marks a function for deferred registration by the scheduler, allowing you to declare dependencies (after) and whether the function should receive the shared state (with_state), and optionally tag the function (tag) for execution filtering. |

### Callbacks

All are optional and run on the scheduler thread (never worker threads).

| Callback | When Fired | Signature |
| --- | --- | --- |
| `on_task_start(fn)`      | Before a task starts | (name) |
| `on_task_run(fn)`        | When tasks starts running on a thread | (name, thread) |
| `on_task_done(fn)`       | After a task finishes | (name, ok) |
| `on_scheduler_start(fn)` | Before scheduler starts running tasks | (meta) |
| `on_scheduler_done(fn)`  | After all tasks complete | (summary) |

### Shared state `_state_lock`

The scheduler exposes a shared re-entrant lock in `state['_state_lock']`. Use this lock only when multiple tasks might write to the same key or mutate the same shared object. For more information refer to [Shared State Guidelines](https://github.com/soda480/threaded-order/blob/main/docs/shared_state.md)

### Interrupt Handling

Press Ctrl-C during execution to gracefully cancel outstanding work:
* Running tasks finish naturally or are marked as cancelled
* Remaining queued tasks are discarded
* Final summary reflects all results

## CLI Overview

A multi-threaded test runner built on top of the threaded-order framework. It uses the dependency DAG to understand relationships between tests and the Scheduler to coordinate safe parallel execution.

Tests that can run together are dispatched across multiple threads, while dependency-bound tests wait for their upstream tasks to complete. This delivers high concurrency without losing deterministic behavior or correctness.

You get:
* Multi-threaded execution handled by the Scheduler
* Deterministic ordering driven by the DAG
* Simple decorator-based test registration
* Clean pass/fail reporting
* Scales well with large or deep dependency graphs
* Ability to filter execution using tags

```bash
usage: mtrun [-h] [--workers WORKERS] [--tags TAGS] [--log] [--verbose] target

A threaded-order CLI for dependency-aware, parallel function execution.

positional arguments:
  target             Python file containing @dmark functions

options:
  -h, --help         show this help message and exit
  --workers WORKERS  Number of worker threads (default: Scheduler default)
  --tags TAGS        Comma-separated list of tags to filter functions by
  --log              enable logging output
  --verbose          enable verbose logging output
```

### Run all functions in a module:

```bash
mtrun path/to/module.py
```
This loads the module, calls optional `setup_state` function, discovers decorated functions, builds the dependency graph, and runs everything with threaded concurrency.

### Run a single function:
```bash
mtrun module.py::function_name
```

If the selected function normally depends on other tasks, ignores those dependencies and runs it standalone. Seed any expected state through the module’s `setup_state` function.

### Pass arbitrary key/value pairs to `setup_state`

Any argument of the form `--key=value` is added to the initial_state dictionary and passed to `setup_state`:
```bash
mtrun module.py --env=dev --region=us-west
```

This allows your module to compute initial state based on CLI parameters.

### Seed mocked results for single-test runs

For functions that depend on upstream results, you can bypass the dependency chain and supply mock values:
```bash
mtrun module.py::test_b --result-test_a=mock_value
```

## Examples

See examples in examples folder. To run examples, follow instructions below to build and run the Docker container then execute:

### Simple [Example](https://github.com/soda480/threaded-order/blob/main/examples/example4.py)

![graph](https://github.com/soda480/threaded-order/blob/main/docs/images/graph.png?raw=true)

<details><summary>Code</summary>

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

</details>

![example4](https://github.com/soda480/threaded-order/blob/main/docs/images/example4.gif?raw=true)

### Shared State [Example](https://github.com/soda480/threaded-order/blob/main/examples/example6.py)

<details><summary>Code</summary>

```Python
import json
from time import sleep
from threaded_order import Scheduler

s = Scheduler(workers=3, state={})

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
print(json.dumps(s.state, indent=2, default=str))
```

</details>

```bash
{
  "_state_lock": "<unlocked _thread.RLock object owner=0 count=0 at 0x7ac9632852c0>",
  "results": {
    "load": "loaded",
    "compute": 15,
    "behave": "behaved"
  },
  "counter": 3,
  "x": 15
}
```

### ProgressBar Integration [Example](https://github.com/soda480/threaded-order/blob/main/examples/example5.py)

Can be done by using the `on_task_done` callback. See [example5](https://github.com/soda480/threaded-order/blob/main/examples/example5.py)

![example5](https://github.com/soda480/threaded-order/blob/main/docs/images/example5.gif?raw=true)

### `mtrun` [Example](https://github.com/soda480/threaded-order/blob/main/examples/example4c.py)

<details><summary>Code</summary>

```Python
import time
import random
from faker import Faker
from threaded_order import dmark, ThreadProxyLogger

logger = ThreadProxyLogger()

def setup_state(state):
    state.update({
        'faker': Faker()
    })

def run(name, state, deps=None, fail=False):
    with state['_state_lock']:
        last_name = state['faker'].last_name()
    sleep = random.uniform(.5, 3.5)
    logger.debug(f'{name} \"{last_name}\" running - sleeping {sleep:.2f}s')
    time.sleep(sleep)
    if fail:
        assert False, 'Intentional Failure'
    else:
        results = []
        for dep in (deps or []):
            dep_result = state['results'].get(dep, '--no-result--')
            results.append(f'{name}.{dep_result}')
        if not results:
            results.append(name)
        logger.info(f'{name} passed')
        return '|'.join(results)

@dmark(with_state=True)
def test_a(state): return run('test_a', state)

@dmark(with_state=True, after=['test_a'])
def test_b(state): return run('test_b', state, deps=['test_a'])

@dmark(with_state=True, after=['test_a'])
def test_c(state): return run('test_c', state, deps=['test_a'])

@dmark(with_state=True, after=['test_c'])
def test_d(state): return run('test_d', state, deps=['test_c'], fail=True)
    
@dmark(with_state=True, after=['test_c'])
def test_e(state): return run('test_e', state, deps=['test_c'])

@dmark(with_state=True, after=['test_b', 'test_d'])
def test_f(state): return run('test_f', state, deps=['test_b', 'test_d'])
```

</details>

![example4c](https://github.com/soda480/threaded-order/blob/main/docs/images/example4c.gif?raw=true)


### `mtrun` tag filtering [Example](https://github.com/soda480/threaded-order/blob/main/examples/example7.py)

<details><summary>Code</summary>

```Python
import time
import random
from faker import Faker
from threaded_order import dmark, tag, ThreadProxyLogger

logger = ThreadProxyLogger()

def setup_state(state):
    state.update({
        'faker': Faker()
    })

def run(name, state, deps=None, fail=False):
    with state['_state_lock']:
        last_name = state['faker'].last_name()
    sleep = random.uniform(.5, 3.5)
    logger.debug(f'{name} \"{last_name}\" running - sleeping {sleep:.2f}s')
    time.sleep(sleep)
    if fail:
        assert False, 'Intentional Failure'
    else:
        results = []
        for dep in (deps or []):
            dep_result = state.get(dep, '--no-result--')
            results.append(f'{name}.{dep_result}')
        if not results:
            results.append(name)
        logger.info(f'{name} passed')
        state[name] = '|'.join(results)

@tag('layer1')
@dmark(with_state=True)
def test_a(state): return run('test_a', state)

@tag('layer2')
@dmark(with_state=True, after=['test_a'])
def test_b(state): return run('test_b', state, deps=['test_a'])

@tag('layer2')
@dmark(with_state=True, after=['test_a'])
def test_c(state): return run('test_c', state, deps=['test_a'])

@tag('layer3')
@dmark(with_state=True, after=['test_c'])
def test_d(state): return run('test_d', state, deps=['test_c'], fail=True)
    
@tag('layer3')
@dmark(with_state=True, after=['test_c'])
def test_e(state): return run('test_e', state, deps=['test_c'])

@tag('layer4')
@dmark(with_state=True, after=['test_b', 'test_d'])
def test_f(state): return run('test_f', state, deps=['test_b', 'test_d'])
```

</details>

![example7](https://github.com/soda480/threaded-order/blob/main/docs/images/example7.gif?raw=true)


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
