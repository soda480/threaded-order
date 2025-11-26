# runner.py
import argparse
import importlib.util
import inspect
from pathlib import Path

from threaded_order import Scheduler


def load_module_from_path(path: str):
    path = Path(path)
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def collect_threaded_tasks(module):
    tasks = []
    for name, obj in inspect.getmembers(module, inspect.isfunction):
        meta = getattr(obj, "__threaded_order__", None)
        if meta is None:
            continue
        tasks.append((name, obj, meta))
    return tasks


def main(argv=None):
    parser = argparse.ArgumentParser(prog="runner")
    parser.add_argument("module_path", help="Path to Python module with tasks")
    parser.add_argument(
        "--workers",
        type=int,
        default=3,
        help="Number of worker threads (default: Scheduler default)",
    )
    args = parser.parse_args(argv)

    # 1) create Scheduler
    sched = Scheduler(workers=args.workers, setup_logging=True)

    # 2) load user module
    mod = load_module_from_path(args.module_path)

    # 3) find all functions marked with @task
    tasks = collect_threaded_tasks(mod)

    if not tasks:
        raise SystemExit(f"No @task functions found in {args.module_path}")

    # 4) register them
    for name, fn, meta in tasks:
        after = meta.get("after") or None
        with_state = bool(meta.get("with_state"))
        # if with_state, Scheduler will pass state when calling the function
        sched.register(fn, name=name, after=after, with_state=with_state)

    # 5) optional callbacks, start scheduler
    def done_cb(summary):
        passed = len(summary["passed"])
        failed = len(summary["failed"])
        print(f"Passed: {passed}  Failed: {failed}")

    sched.on_scheduler_done(done_cb)
    sched.start()


if __name__ == "__main__":
    main()
