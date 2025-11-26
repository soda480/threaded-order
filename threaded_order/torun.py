import sys
import argparse
import json
import importlib.util
import inspect
from pathlib import Path
from threaded_order import Scheduler, ThreadProxyLogger

logger = ThreadProxyLogger()

def get_parser():
    """ return argument parser
    """
    parser = argparse.ArgumentParser(
        prog='torun',
        description='A threaded-order CLI for dependency-aware, parallel function execution.')
    parser.add_argument(
        'target',
        help='Python file containing @dmark tasks, optionally with a test selector')
    parser.add_argument(
        '--workers',
        type=int,
        default=3,
        help='Number of worker threads (default: Scheduler default)')
    parser.add_argument(
        '--log',
        action='store_true',
        help='enable logging output')
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='enable verbose logging output')
    return parser

def parse_setup_kwargs(unknown_args):
    """ parse arbitrary --key=value pairs from the unknown args list
        Example:
        ["--env=dev", "--region=us-west-2"] -> {"env": "dev", "region": "us_west_2"}
    """
    kwargs = {}
    for item in unknown_args:
        if not item.startswith('--'):
            continue
        if '=' not in item:
            continue
        key, value = item[2:].split('=', 1)
        kwargs[key] = value

    clear_results_on_start = True
    if any(key.startswith('result-') for key in kwargs.keys()):
        clear_results_on_start = False
    return kwargs, clear_results_on_start

def split_target(target):
    """ split 'module.py::test_name' into (module_path, test_name)
        if no '::' is present, return (target, None).
    """
    if '::' in target:
        module_path, func_name = target.split('::', 1)
        return module_path, func_name
    return target, None

def load_module(path):
    """ load a module from a given file path
    """
    path = Path(path)
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def collect_dmarked_functions(module):
    """ return (name, function, meta) for all functions marked by @dmark."""
    tasks = []
    for name, function in inspect.getmembers(module, inspect.isfunction):
        meta = getattr(function, '__threaded_order__', None)
        if meta is None:
            continue
        tasks.append((name, function, meta))
    return tasks

def _main(argv=None):
    """ main entry point
    """
    parser = get_parser()

    args, unknown = parser.parse_known_args(argv)
    setup_kwargs, clear_results_on_start = parse_setup_kwargs(unknown)

    module_path, selected_test = split_target(args.target)
    module = load_module(module_path)

    initial_state = None
    setup_state_function = getattr(module, 'setup_state', None)
    if callable(setup_state_function):
        initial_state = setup_state_function(**setup_kwargs)

    scheduler_kwargs = {
        'workers': args.workers,
        'setup_logging': args.log,
        'clear_results_on_start': clear_results_on_start,
        'verbose': args.verbose,
    }
    if initial_state is not None:
        scheduler_kwargs['state'] = initial_state

    scheduler = Scheduler(**scheduler_kwargs)
    tasks = collect_dmarked_functions(module)
    if not tasks:
        raise SystemExit(f'No @dmark functions found in {module_path}')

    if selected_test is not None:
        filtered = [test for test in tasks if test[0] == selected_test]
        if not filtered:
            raise SystemExit(
                f"test '{selected_test}' not found or not marked with @dmark in {module_path}")
        tasks = filtered
    single_test_mode = selected_test is not None

    for name, function, meta in tasks:
        after = meta.get('after') or None
        with_state = bool(meta.get('with_state'))
        if single_test_mode and after:
            # break dependency edges so Scheduler doesn't complain
            after = []
        scheduler.register(function, name=name, after=after, with_state=with_state)

    def on_done(summary):
        passed = len(summary["passed"])
        failed = len(summary["failed"])
        print(f"==== {passed} passed, {failed} failed in {summary['duration']:.2f}s ====")

    summary = scheduler.start()
    logger.debug(json.dumps(scheduler.state['results'], indent=2))
    on_done(summary)

def main(argv=None):
    """ main entry point with error handling
    """
    try:
        _main(argv)
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
