import ast
import re
import sys
import argparse
import json
import importlib.util
import inspect
from contextlib import nullcontext
from pathlib import Path
from threaded_order import Scheduler, ThreadProxyLogger, default_workers
from threaded_order.graph_summary import format_graph_summary
from threaded_order.scheduler import TaskStatus
try:
    from progress1bar import ProgressBar
    HAS_PROGRESS_BAR = True
except ImportError:
    HAS_PROGRESS_BAR = False
try:
    from thread_viewer import ThreadViewer
    HAS_VIEWER = True
except ImportError:
    HAS_VIEWER = False

logger = ThreadProxyLogger()

def get_parser():
    """ return argument parser
    """
    parser = argparse.ArgumentParser(
        prog='tdrun',
        description='A threaded-order CLI for dependency-aware, parallel function execution.')
    parser.add_argument(
        'target',
        help='Python file containing @mark functions')
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
    parser.add_argument(
        '--progress',
        action='store_true',
        help='show progress bar (requires progress1bar package)')
    parser.add_argument(
        '--viewer',
        action='store_true',
        help='show thread viewer visualizer (requires thread-viewer package)')
    return parser

def get_initial_state(unknown_args):
    """ parse arbitrary --key=value pairs from the unknown args list
        Example:
        ["--env=dev", "--region=us_west_2"] -> {"env": "dev", "region": "us_west_2"}
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
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from '{path}'")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def get_functions(module):
    """ yield (name, function, is_async) for top-level defs in source order.
    """
    module_path = inspect.getsourcefile(module)
    if not module_path:
        raise SystemExit('Could not determine source file for target module')

    with open(module_path, 'r', encoding='utf-8') as f:
        tree = ast.parse(f.read(), filename=module_path)

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            function = getattr(module, node.name, None)
            if inspect.isfunction(function):
                yield node.name, function, isinstance(node, ast.AsyncFunctionDef)

def collect_functions(module, tags_filter=None):
    """ return (name, function, meta) for all functions marked by @mark.
    """
    functions = []
    module_path = inspect.getsourcefile(module) or '<unknown>'

    for name, function, is_async in get_functions(module):
        meta = getattr(function, '__threaded_order__', None)
        if meta is None:
            continue

        if is_async:
            raise SystemExit(f"Async @mark functions are not supported: '{name}' in {module_path}")

        if tags_filter:
            tags = meta.get('tags') or []
            if any(t not in tags for t in tags_filter):
                continue

        functions.append((name, function, meta))

    return functions

def _setup_output(scheduler, args):
    """ configure progress output based on args
    """
    total = len(scheduler.graph.nodes())
    if args.progress:
        if not HAS_PROGRESS_BAR:
            raise SystemExit('progress1bar package is required for progress bar output')

        def on_task_done(task_name, thread_name, status, count, total, pb, *args):
            pb.count += 1
            pb.alias = task_name

        pb = ProgressBar(total=total, show_complete=False, clear_alias=True)
        scheduler.on_task_done(on_task_done, total, pb)
        return pb

    elif args.viewer:
        if not HAS_VIEWER:
            raise SystemExit('thread-viewer package is required for thread viewer output')

        def on_task_run(task_name, thread_name, viewer, *args):
            viewer.run(thread_name)

        def on_task_done(task_name, thread_name, status, count, viewer, *args):
            viewer.done(thread_name)

        viewer = ThreadViewer(thread_count=args.workers, task_count=total, thread_prefix='thread_')
        scheduler.on_task_run(on_task_run, viewer)
        scheduler.on_task_done(on_task_done, viewer)
        return viewer

    else:
        if not args.log:
            def on_task_done(name, thread_name, status, count, total):
                if status == TaskStatus.PASSED:
                    char = '.'
                elif status == TaskStatus.FAILED:
                    char = 'f'
                else:
                    char = 's'
                print(char, end='', flush=True)

            scheduler.on_task_done(on_task_done, total)
            scheduler.on_scheduler_done(lambda s: print('', flush=True))
        else:
            def on_task_done(name, thread_name, status, count, total):
                _percent = int((count / total) * 100)
                percent = f'{status.value} [{_percent:3d}% ]'
                base = f'[{_pad_thread_name(thread_name, args.workers)}] {name}' \
                    if thread_name else name
                dots = '.' * max(0, 75 - len(base) - len(percent))
                logger.info(f'{base} {dots} {percent}')

            scheduler.on_task_done(on_task_done, total)
        return nullcontext()

def _pad_thread_name(name, workers):
    """ pad thread name numbers with leading zeros for consistent width
    """
    width = len(str(workers - 1))
    return re.sub(r'(\d+)$', lambda m: m.group(1).zfill(width), name)

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
    """ collect @mark functions and apply tag and name filtering
    """
    marked_functions = collect_functions(module, tags_filter=tags_filter)
    if not marked_functions:
        raise SystemExit(
            f'No @mark functions found in {module_path} '
            'or no functions match the given tags filter')

    single_function_mode = False
    if function_name is not None:
        filtered = [f for f in marked_functions if f[0] == function_name]
        if not filtered:
            raise SystemExit(
                f"function '{function_name}' not found or "
                f"not marked with @mark in {module_path} or "
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
        'skip_dependents': args.skip_deps
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
        scheduler_kwargs['add_stream_handler'] = not args.progress and not args.viewer

    return scheduler_kwargs

def validate_args(args):
    """ validate parsed args
    """
    if args.progress and not HAS_PROGRESS_BAR:
        raise SystemExit(
            'Error: progress1bar package is required for progress bar output')
    if args.progress and args.verbose:
        raise SystemExit(
            'Error: the --progress and --verbose arguments cannot be used together')
    if args.viewer and not HAS_VIEWER:
        raise SystemExit(
            'Error: thread-viewer package is required for viewer output')
    if args.viewer and args.verbose:
        raise SystemExit(
            'Error: the --viewer and --verbose arguments cannot be used together')
    if args.progress and args.viewer:
        raise SystemExit('Error: --progress and --viewer cannot be used together')
    if args.workers < 1:
        raise SystemExit('Error: --workers must be >= 1')

def _main(argv=None):
    """ main CLI entry point
    """
    parser = get_parser()

    # parse args and initialize shared state
    args, unknown_args = parser.parse_known_args(argv)
    validate_args(args)
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

    with _setup_output(scheduler, args):
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
        args = argv if argv is not None else sys.argv[1:]
        if '--verbose' in args:
            raise
        print(f'Error: {e}')
        sys.exit(1)

if __name__ == '__main__':
    main()
