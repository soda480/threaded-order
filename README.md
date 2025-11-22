[![ci](https://github.com/soda480/threaded-order/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/soda480/threaded-order/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/threaded-order.svg)](https://badge.fury.io/py/threaded-order)

# threaded-order
A lightweight Python framework for running functions concurrently across multiple threads while maintaining defined execution order. It lets you declare dependencies between tasks—so some run only after others complete—without complex orchestration code. 

Ideal for dependency-aware test execution, build pipelines, and automation workflows that benefit from controlled concurrency.

Key Features
* Concurrent task execution using Python threads
* Dependency graph automatically determines order
* Simple registration and decorator API
* Thread-safe logging, callbacks, and run summary
* Graceful shutdown on interrupt

## Installation

```
pip install threaded-order
```

## Simple Example
```
from threaded_order import Scheduler, ThreadProxyLogger
from time import sleep

s = Scheduler(workers=3, setup_logging=True)
logger = ThreadProxyLogger()

@s.dregister()
def a(): sleep(1); logger.info("a")

@s.dregister(after=['a'])
def b(): sleep(1); logger.info("b")

@s.dregister(after=['a'])
def c(): sleep(1); logger.info("c")

@s.dregister(after=['b', 'c'])
def d(): sleep(1); logger.info("d")

if __name__ == '__main__':
    s.on_scheduler_done(lambda s: print(f"Passed:{len(s['passed'])} Failed:{len(s['failed'])}"))
    s.start()
```

Output:
```
2025-11-11 22:07:33 [MainThread]: starting thread pool with 3 threads
2025-11-11 22:07:34 [thread_0]: a
2025-11-11 22:07:35 [thread_1]: c
2025-11-11 22:07:35 [thread_0]: b
2025-11-11 22:07:36 [thread_1]: d
2025-11-11 22:07:36 [MainThread]: all work completed
2025-11-11 22:07:36 [MainThread]: duration: 3.01s
Passed:4 Failed:0
```
### ProgressBar Integration

Can be done by using the `on_task_done` callback. See [example3b](https://github.com/soda480/threaded-order/blob/main/examples/example3b.py)

![example1](https://github.com/soda480/threaded-order/blob/main/docs/images/example3b.gif?raw=true)


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
