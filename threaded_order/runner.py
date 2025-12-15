import ast
import os
import sys
import argparse
import json
import importlib.util
import inspect
from pathlib import Path
from threaded_order import Scheduler, ThreadProxyLogger, default_workers
from threaded_order.graph_summary import format_graph_summary


logger = ThreadProxyLogger()

def get_parser():
    """ return argument parser
    """
    parser = argparse.ArgumentParser(
        prog='tdrun',
        description='A threaded-order CLI for dependency-aware, parallel function execution.')
    parser.add_argument(
        'target',
        help='Python file containing @dmark functions')
    parser.add_argument(
        '--workers',
        type=int,
        default=default_workers,
        help='Number of worker threads (default: Scheduler default)')
    parser.add_argument(
        '--tags',
        type=str,
        default=None,
        help='Comma-separated list of tags to filter functions by')
    parser.add_argument(
        '--log',
        action='store_true',
        help='enable logging output')
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='enable verbose logging output')
    parser.add_argument(
        '--graph',
        action='store_true',
        help='show dependency graph and exit')
    parser.add_argument(
        '--skip-deps',
        action='store_true',
        help='skip functions whose dependencies failed')
    return parser

def get_initial_state(unknown_args):
    """ parse arbitrary --key=value pairs from the unknown args list
        Example:
        ["--env=dev", "--region=us-west-2"] -> {"env": "dev", "region": "us_west_2"}
    """
    initial_state = {}
    clear_results_on_start = True
    for item in unknown_args:
        if not item.startswith('--'):
            continue
        if '=' not in item:
            continue
        key, value = item[2:].split('=', 1)
        if key.startswith('result-'):
            test_name = key[len('result-'):]
            initial_state.setdefault('results', {})[test_name] = value
            clear_results_on_start = False
        else:
            initial_state[key] = value
    return initial_state, clear_results_on_start

def split_target(target):
    """ split 'module.py::test_name' into (module_path, test_name)
        if no '::' is present, return (target, None).
    """
    if '::' in target:
        module_path, function_name = target.split('::', 1)
        return module_path, function_name
    return target, None

def load_module(path):
    """ load a module from a given file path
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Module file '{path}' not found")
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def get_functions(module):
    """ yield (name, function) for all functions defined as they appear in the module
    """
    module_path = inspect.getsourcefile(module)
    with open(module_path, 'r') as f:
        tree = ast.parse(f.read(), filename=module_path)
    function_names = [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]
    for function_name in function_names:
        function = getattr(module, function_name)
        if inspect.isfunction(function):
            yield function_name, function

def collect_functions(module, tags_filter=None):
    """ return (name, function, meta) for all functions marked by @dmark.
    """
    functions = []
    for name, function in get_functions(module):
        meta = getattr(function, '__threaded_order__', None)
        if meta is None:
            continue
        if tags_filter:
            tags = meta.get('tags')
            if any(t not in tags for t in tags_filter):
                continue
        functions.append((name, function, meta))
    return functions

def _maybe_setup_minimal_progress_output(scheduler, args):
    """ configure minimal stdout progress when logging is disabled
    """
    if args.log:
        return

    # suppress scheduler logging noise
    sys.stderr = open(os.devnull, 'w')

    def on_task_done(name, ok):
        print('.' if ok else '*', end='', flush=True)

    scheduler.on_task_done(on_task_done)
    scheduler.on_scheduler_done(lambda s: print('', flush=True))

def _register_functions(scheduler, marked_functions, tags_filter, single_function_mode):
    """ register collected functions with the scheduler

        handles dependency stripping for single-function mode and
        dependency pruning when tag filtering is active.
    """
    allowed_names = ({name for name, _, _ in marked_functions} if tags_filter else None)

    for name, function, meta in marked_functions:
        after = meta.get('after') or None
        with_state = bool(meta.get('with_state'))

        # break dependency edges when running a single function
        if single_function_mode and after:
            after = []

        # remove dependencies filtered out by tags
        if after and allowed_names is not None:
            # exclude dependencies that are missing due to tag filtering
            after = [d for d in after if d in allowed_names]

        scheduler.register(function, name=name, after=after, with_state=with_state)

def _collect_and_filter_functions(module, module_path, tags_filter, function_name):
    """ collect @dmark functions and apply tag and name filtering
    """
    marked_functions = collect_functions(module, tags_filter=tags_filter)
    if not marked_functions:
        raise SystemExit(
            f'No @dmark functions found in {module_path} '
            'or no functions match the given tags filter')

    single_function_mode = False
    if function_name is not None:
        filtered = [f for f in marked_functions if f[0] == function_name]
        if not filtered:
            raise SystemExit(
                f"function '{function_name}' not found or "
                f"not marked with @dmark in {module_path} or "
                'does not match the given tags filter')
        marked_functions = filtered
        single_function_mode = True

    return marked_functions, single_function_mode

def _parse_tags_filter(tags):
    """ parse comma-separated tag list into a normalized filter list
    """
    if not tags:
        return []
    return [t.strip() for t in tags.split(',') if t.strip()]

def _maybe_call_setup_state(module, initial_state):
    """ invoke module-level setup_state(initial_state) if defined
    """
    setup_state_function = getattr(module, 'setup_state', None)
    if callable(setup_state_function):
        setup_state_function(initial_state)

def _build_scheduler_kwargs(args, initial_state, clear_results_on_start, module):
    """ build Scheduler constructor kwargs and configure logging if requested
    """
    scheduler_kwargs = {
        'workers': args.workers if args.workers else None,
        'state': initial_state,
        'clear_results_on_start': clear_results_on_start,
        'skip_dependents': args.skip_deps,
    }

    if not args.log:
        return scheduler_kwargs

    # prefer module-provided logging hook if available
    setup_logging_function = getattr(module, 'setup_logging', None)
    if callable(setup_logging_function):
        setup_logging_function(args.workers, args.verbose)
    else:
        scheduler_kwargs['setup_logging'] = True
        scheduler_kwargs['verbose'] = args.verbose

    return scheduler_kwargs

def _main(argv=None):
    """ main CLI entry point
    """
    parser = get_parser()

    # parse args and initialize shared state
    args, unknown_args = parser.parse_known_args(argv)
    initial_state, clear_results_on_start = get_initial_state(unknown_args)

    # load target module and resolve target function
    module_path, function_name = split_target(args.target)
    module = load_module(module_path)

    # build scheduler configuration and configure logging
    scheduler_kwargs = _build_scheduler_kwargs(args, initial_state, clear_results_on_start, module)

    # allow module to mutate initial state if supported
    _maybe_call_setup_state(module, initial_state)

    scheduler = Scheduler(**scheduler_kwargs)

    # collect and optionally filter marked functions
    tags_filter = _parse_tags_filter(args.tags)
    marked_functions, single_function_mode = _collect_and_filter_functions(
        module, module_path, tags_filter, function_name)

    logger.info(f'collected {len(marked_functions)} marked functions')
    _register_functions(scheduler, marked_functions, tags_filter, single_function_mode)

    if args.graph:
        print(format_graph_summary(scheduler.graph))
        return

    _maybe_setup_minimal_progress_output(scheduler, args)

    summary = scheduler.start()

    # debug final state and print user-facing summary
    logger.debug('Scheduler::State: ' + json.dumps(scheduler.state, indent=2, default=str))
    print(summary['text'])

    if summary.get('failed'):
        sys.exit(1)

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
