[![ci](https://github.com/soda480/threaded-order/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/soda480/threaded-order/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/threaded-order.svg)](https://badge.fury.io/py/threaded-order)

# threaded-order
A lightweight Python framework for running functions concurrently across multiple threads while maintaining a defined execution order. It lets you declare relationships between tasks—so some run only after others complete—without building complex orchestration logic. Perfect for dependency-aware test execution, build pipelines, or automation flows that benefit from controlled concurrency.

Key features:
* Executes functions concurrently with Python threads
* Dependency graph determines execution order
* Simple base class for registering and managing tasks
* Thread-safe logging and status tracking

## Installation

```
pip install threaded-order
```

## Usage

See examples in examples folder. To run examples, follow instructions below to build and run the Docker container then execute:

```
python -m pip install -e .[dev]
```

```
python examples/example1.py
2025-11-10 00:08:31 [thread_M]: starting thread pool with 5 threads
2025-11-10 00:08:37 [thread_1]: i02 completed
2025-11-10 00:08:39 [thread_0]: i01 completed
2025-11-10 00:08:40 [thread_2]: i03 completed
2025-11-10 00:08:40 [thread_3]: i04 completed
2025-11-10 00:08:44 [thread_3]: i07 completed
2025-11-10 00:08:47 [thread_0]: i05 completed
2025-11-10 00:08:48 [thread_1]: i06 completed
2025-11-10 00:08:52 [thread_1]: i10 completed
2025-11-10 00:08:53 [thread_0]: i09 completed
2025-11-10 00:08:56 [thread_3]: i08 completed
2025-11-10 00:08:59 [thread_1]: i11 completed
2025-11-10 00:09:00 [thread_0]: i12 completed
2025-11-10 00:09:01 [thread_3]: i13 completed
2025-11-10 00:09:03 [thread_1]: i14 completed
2025-11-10 00:09:07 [thread_0]: i15 completed
2025-11-10 00:09:09 [thread_3]: i16 completed
2025-11-10 00:09:20 [thread_3]: i17 completed
2025-11-10 00:09:20 [thread_M]: all work completed
2025-11-10 00:09:20 [thread_M]: duration: 48.89s
```

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
