import os
import time
import queue
import threading
import logging
from collections import defaultdict, Counter
from concurrent.futures import ThreadPoolExecutor, CancelledError
from functools import wraps
from .logger import configure_logging

class ThreadedOrder:
    """ run functions concurrently across multiple threads while maintaining a defined
        execution order
    """
    max_workers = min(8, os.cpu_count())

    def __init__(self, workers=max_workers, setup_logging=False, add_stream_handler=True):
        """ initialize scheduler with thread pool size, logging, and callback placeholders
        """
        # number of concurrent worker threads in the pool
        self._workers = workers
        # task name → callable object to execute
        self._run_map = {}
        # task name → list of dependency names (parents)
        self._dgraph = defaultdict(list)
        # task name → set of dependents (children) for fast removal
        self._children = defaultdict(set)
        # protects access to _futures (shared by scheduler and worker threads)
        self._lock = threading.Lock()
        # currently running task names
        self._active = set()
        # future → task name mapping for cancellation and error recovery
        self._futures = {}
        # signals scheduler when all tasks have completed
        self._completed = threading.Event()
        # ThreadPoolExecutor instance (managed inside start())
        self._executor = None
        # thread-safe queue for passing start/done events from workers to scheduler
        self._events = queue.Queue()
        # wall-clock start time (UTC seconds)
        self._started_wall = 0.0
        # wall-clock finish time (UTC seconds)
        self._finished_wall = 0.0
        # monotonic clock start time (for precise duration measurement)
        self._started_mono = 0.0
        # monotonic clock finish time (for precise duration measurement)
        self._finished_mono = 0.0
        # list of task names that have run (in order of completion)
        self._ran = []
        # task name → result details (ok, error_type, error)
        self._results = {}
        # list of task names that failed
        self._failed = []
        # user callback fired when a task is about to start
        self._on_task_start = None
        # user callback fired when a task completes
        self._on_task_done = None
        # user callback fired when the scheduler begins execution
        self._on_scheduler_start = None
        # user callback fired when the scheduler finishes all tasks
        self._on_scheduler_done = None
        self._prefix = 'thread'
        if setup_logging:
            configure_logging(workers, prefix=self._prefix, add_stream_handler=add_stream_handler)

    def register(self, obj, name, after=None):
        """ register a callable for execution, optionally dependent on other tasks
        """
        if not callable(obj):
            raise ValueError('object must be callable')
        logger = logging.getLogger(threading.current_thread().name)
        logger.debug(f'add {name} dependent on {after}')
        if name in self._run_map:
            raise ValueError(f'{name} has already been added')
        after = after or []
        unknowns = [dname for dname in after if dname not in self._run_map]
        if unknowns:
            raise ValueError(f'{name} depends on unknown {unknowns}')
        self._run_map[name] = obj
        self._dgraph[name] = []
        for dname in after:
            self._dgraph[name].append(dname)
            self._children[dname].add(name)
        if self._has_cycle():
            raise ValueError(f'adding {name} will create a cycle')

    def dregister(self, after=None):
        """ decorator form of register() for convenient inline task definition
        """
        def decorator(function):
            @wraps(function)
            def wrapper(*args, **kwargs):
                return function(*args, **kwargs)
            # register at decoration time so start() can discover it
            self.register(wrapper, function.__name__, after=after)
            # keep a pointer to the original
            wrapper.__original__ = function
            return wrapper
        return decorator

    def _has_cycle(self):
        """ return True if dependency graph contains a cycle
        """
        visited = set()
        stack = set()

        def visit(node):
            if node in stack:
                return True
            if node in visited:
                return False
            visited.add(node)
            stack.add(node)
            for neighbor in self._dgraph[node]:
                if visit(neighbor):
                    return True
            stack.remove(node)
            return False
        return any(visit(node) for node in self._run_map)

    def _unregister(self, rname):
        """ remove a completed task from all dependency lists
        """
        logger = logging.getLogger(threading.current_thread().name)
        for name in self._children.pop(rname, ()):
            logger.debug(f'removing {rname} as a dependency from {name}')
            self._dgraph[name].remove(rname)
        if rname in self._dgraph and not self._dgraph[rname]:
            logger.debug(f'removing {rname} from dependency graph')
            del self._dgraph[rname]

    def _get_cands(self, number):
        """ return up to `number` tasks whose dependencies are satisfied and not active
        """
        def _get_msg(found):
            count = len(found)
            if count == 0:
                message = 'but found no candidates eligible for submission'
            elif count == 1:
                message = 'and found 1 candidate eligible for submission'
            else:
                message = f'and found {count} candidates eligible for submission'
            return f"{message} {', '.join(found)}"
        logger = logging.getLogger(threading.current_thread().name)
        # ensure candidate selection stability for reproducable runs by sorting
        cands = sorted([
            name for name, deps in self._dgraph.items() if not deps and name not in self._active])
        cands = cands[:number]
        logger.debug(f'requested {number} {_get_msg(cands)}')
        return cands

    def _handle_events(self):
        """ process queued task and scheduler events on the scheduler thread
        """
        logger = logging.getLogger(threading.current_thread().name)
        while True:
            try:
                kind, payload = self._events.get_nowait()
            except queue.Empty:
                break

            if kind == 'start':
                name = payload
                self._callback(self._on_task_start, name)

            elif kind == 'done':
                name, ok, error_type, error = payload
                logger.debug(f'removing {name!r} from active futures')
                self._active.discard(name)
                self._unregister(name)

                self._ran.append(name)
                self._results[name] = {
                    'ok': ok,
                    'error_type': error_type,
                    'error': error
                }
                if not ok:
                    self._failed.append(name)

                self._callback(self._on_task_done, name, ok)
                # schedule next candidate
                free = max(0, self._workers - len(self._active))
                if free:
                    # keep pool full after dependency 'burst' - several tasks unblock at once
                    for cand in self._get_cands(free):
                        self._submit(cand)
                if not self._dgraph and not self._active:
                    logger.debug(
                        'nothing more to run and no active futures remain - signaling all done')
                    self._completed.set()

    def _build_summary(self):
        """ assemble concise run summary from collected results and timings
        """
        ran = list(self._ran)
        passed = [name for name, result in self._results.items() if result["ok"]]
        failed = list(self._failed)
        failures = {
            name: {
                'error_type': self._results[name]['error_type'],
                'error': self._results[name]['error']
            } for name in failed
        }
        failure_counts = Counter(
            result['error_type'] for result in self._results.values() if not result['ok']
        )
        return {
            'ran': ran,
            'passed': passed,
            'failed': failed,
            'failures': failures,
            'failure_counts': dict(failure_counts),
            'started_at': self._started_wall,
            'finished_at': self._finished_wall,
            'duration': self._finished_mono - self._started_mono
        }

    def _handle_interrupt(self, logger):
        """ cancel in-flight work, drain events, and mark remaining tasks as cancelled
        """
        logger.error('interrupt received; cancelling remaining tasks')

        # cancel all futures we still track
        with self._lock:
            futures = list(self._futures.keys())
        for future in futures:
            try:
                future.cancel()
            except (CancelledError, RuntimeError) as exception:
                logger.debug(f'cancel() ignored for completed future: {exception}')

        # drain anything already completed and queued
        self._handle_events()

        # mark any still-active tasks as cancelled (these never emitted a 'done' event)
        still_active = list(self._active)
        self._active.clear()
        for name in still_active:
            # remove from graph so completion logic won't wait on them
            self._unregister(name)
            # record cancellation
            self._ran.append(name)
            self._results[name] = {
                'ok': False,
                'error_type': 'CancelledError',
                'error': 'cancelled'
            }
            self._failed.append(name)

        # signal completion so the loop (if resumed) would exit
        self._completed.set()

    def start(self):
        """ run all registered tasks respecting dependencies, collect results, and trigger callbacks
        """
        logger = logging.getLogger(threading.current_thread().name)
        self._ran.clear()
        self._results.clear()
        self._failed.clear()
        self._completed.clear()
        self._futures.clear()

        # drain any stale events
        try:
            while True:
                self._events.get_nowait()
        except queue.Empty:
            pass

        self._started_wall = time.time()
        self._started_mono = time.perf_counter()
        meta = {
            'total_tasks': len(self._run_map),
            'workers': self._workers,
            'started_at': self._started_wall
        }
        self._callback(self._on_scheduler_start, meta)

        try:
            with ThreadPoolExecutor(max_workers=self._workers,
                                    thread_name_prefix=self._prefix) as executor:
                self._executor = executor
                logger.info(f'starting thread pool with {self._workers} threads')
                # initial seeding
                for name in self._get_cands(self._workers):
                    self._submit(name)

                # main loop of scheduler thread
                while not self._completed.wait(timeout=0.1):
                    self._handle_events()

                # final drain
                self._handle_events()
                logger.info('all work completed')

        except KeyboardInterrupt:
            self._handle_interrupt(logger)

        finally:
            self._finished_wall = time.time()
            self._finished_mono = time.perf_counter()
            duration = self._finished_mono - self._started_mono
            logger.info(f'duration: {duration:.2f}s')
            summary = self._build_summary()
            self._callback(self._on_scheduler_done, summary)
            return summary

    def _submit(self, name):
        """ submit a ready task to the thread pool and queue its start event
        """
        logger = logging.getLogger(threading.current_thread().name)
        logger.debug(f'submitting {name!r} to thread pool')

        self._events.put(('start', name))

        future = self._executor.submit(self._run, name)
        logger.debug(f'adding {name} to active futures')
        self._active.add(name)
        with self._lock:
            # track future to name
            self._futures[future] = name
        future.add_done_callback(self._done)

    def _done(self, future):
        """ enqueue a 'done' event for a finished Future
            safely extracts the task result or synthesizes a failure if the Future raised
        """
        try:
            payload = future.result()
        except Exception as exception:
            # worker failed before building payload - recover name and emit synthetic failure
            name = self._futures.get(future, '<unknown>')
            payload = (name, False, type(exception).__name__, str(exception))
        finally:
            # cleanup no matter what
            with self._lock:
                self._futures.pop(future, '<unknown>')
        self._events.put(('done', payload))

    def _run(self, name):
        """ execute a task callable, capture errors, and return its result tuple
        """
        logger = logging.getLogger(threading.current_thread().name)
        logger.debug(f'run {name!r}')
        ok = True
        error_type = None
        error = None
        try:
            self._run_map[name]()
        except Exception as exception:
            ok = False
            error_type = type(exception).__name__
            error = str(exception)
            logger.error(f'{name!r} failed: {error_type}: {error}')
        return (name, ok, error_type, error)

    def __repr__(self):
        """ return a human-readable representation of the dependency graph
        """
        rstr = '\n'.join([f'{name}: {deps}' for name, deps in self._dgraph.items()])
        rstr1 = '\n'.join([f'{dep}: {name}' for dep, name in self._children.items()])
        return f'Dependency Graph:\n{rstr}\nChildren:\n{rstr1}'

    def _callback(self, callback, *args):
        """ safely invoke a user callback, logging any exceptions raised
        """
        if not callback:
            return
        logger = logging.getLogger(threading.current_thread().name)
        try:
            callback(*args)
        except Exception:
            callback_name = getattr(callback, '__name__', callback)
            logger.debug(f'callback {callback_name!r} failed', exc_info=True)

    def on_task_start(self, function):
        """ register callback fired when a task is about to start
        """
        self._on_task_start = function

    def on_task_done(self, function):
        """ register callback fired when a task finishes execution
        """
        self._on_task_done = function

    def on_scheduler_start(self, function):
        """ register callback fired when the scheduler begins execution
        """
        self._on_scheduler_start = function

    def on_scheduler_done(self, function):
        """ register callback fired when the scheduler completes all tasks
        """
        self._on_scheduler_done = function
