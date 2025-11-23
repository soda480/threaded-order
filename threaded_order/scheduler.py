import os
import queue
import threading
import logging
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, CancelledError
from functools import wraps
from .graph import DAGraph
from .timer import Timer
from .logger import configure_logging


class Scheduler:
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
        self._callables = {}
        # direct acyclic graph
        self._graph = DAGraph()
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

        # timing info
        self._timer = Timer()

        # results tracking
        self._ran = []
        self._results = {}
        self._failed = []

        # user-defined callbacks
        self._on_task_start = None
        self._on_task_run = None
        self._on_task_done = None
        self._on_scheduler_start = None
        self._on_scheduler_done = None

        self._prefix = 'thread'
        if setup_logging:
            configure_logging(workers, prefix=self._prefix, add_stream_handler=add_stream_handler)

    def register(self, obj, name, after=None):
        """ register a callable for execution, optionally dependent on other tasks
        """
        if not callable(obj):
            raise ValueError('object must be callable')
        self._graph.add(name, after=after)
        self._callables[name] = obj

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

    def _handle_event(self):
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

            elif kind == 'run':
                name, thread = payload
                self._callback(self._on_task_run, name, thread)

            elif kind == 'done':
                name, ok, error_type, error = payload
                logger.debug(f'removing {name!r} from active futures')
                self._active.discard(name)
                self._graph.remove(name)
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
                    for cand in self._graph.get_candidates(self._active, free):
                        self._submit(cand)

                # check for overall completion
                if self._graph.is_empty() and not self._active:
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
            'started_at': self._timer.started_at,
            'finished_at': self._timer.finished_at,
            'duration': self._timer.duration
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
        self._handle_event()

        # mark any still-active tasks as cancelled (these never emitted a 'done' event)
        still_active = list(self._active)
        self._active.clear()
        for name in still_active:
            # remove from graph so completion logic won't wait on them
            self._graph.remove(name)
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

    def _prep_start(self):
        """ prepare internal state for a fresh run
        """
        # reset tracking structures
        self._ran.clear()
        self._results.clear()
        self._failed.clear()
        self._completed.clear()
        self._futures.clear()
        self._active.clear()
        # drain any stale events
        try:
            while True:
                self._events.get_nowait()
        except queue.Empty:
            pass

    def start(self):
        """ run all registered tasks respecting dependencies, collect results, and trigger callbacks
        """
        logger = logging.getLogger(threading.current_thread().name)

        self._prep_start()

        self._timer.start()
        meta = {
            'total_tasks': len(self._callables),
            'workers': self._workers,
            'start_time': self._timer.started_at
        }
        self._callback(self._on_scheduler_start, meta)

        try:
            with ThreadPoolExecutor(max_workers=self._workers,
                                    thread_name_prefix=self._prefix) as executor:
                self._executor = executor
                logger.info(f'starting thread pool with {self._workers} threads')
                # initial seeding
                for name in self._graph.get_candidates(self._active, self._workers):
                    self._submit(name)

                # main loop of scheduler thread
                while not self._completed.wait(timeout=0.1):
                    self._handle_event()

                # final drain
                self._handle_event()
                logger.info('all work completed')

        except KeyboardInterrupt:
            self._handle_interrupt(logger)

        finally:
            self._timer.stop()
            logger.info(f'duration: {self._timer.duration:.2f}s')

            # build and return summary
            summary = self._build_summary()
            self._callback(self._on_scheduler_done, summary)
            return summary

    def _submit(self, name):
        """ submit a ready task to the thread pool and queue its start event
        """
        logger = logging.getLogger(threading.current_thread().name)
        logger.debug(f'submitting {name!r} to thread pool')

        # queue 'start' event
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

        # queue 'done' event
        self._events.put(('done', payload))

    def _run(self, name):
        """ execute a task callable, capture errors, and return its result tuple
        """
        thread = threading.current_thread().name
        logger = logging.getLogger(thread)

        # queue 'run' event
        payload = (name, thread)
        self._events.put(('run', payload))

        logger.debug(f'run {name!r}')
        ok = True
        error_type = None
        error = None
        try:
            self._callables[name]()
        except Exception as exception:
            ok = False
            error_type = type(exception).__name__
            error = str(exception)
            logger.error(f'{name!r} failed: {error_type}: {error}')
        return (name, ok, error_type, error)

    def _callback(self, callback, *args):
        """ safely invoke a user callback, logging any exceptions raised
        """
        if not callback:
            return
        logger = logging.getLogger(threading.current_thread().name)
        try:
            if isinstance(callback, tuple):
                function, user_args, user_kwargs = callback
                function(*args, *user_args, **user_kwargs)
            else:
                callback(*args)
        except Exception:
            callback_name = getattr(callback, '__name__', callback)
            logger.debug(f'callback {callback_name!r} failed', exc_info=True)

    def on_task_start(self, function, *args, **kwargs):
        """ register callback fired when a task is about to start
        """
        self._on_task_start = (function, args, kwargs)

    def on_task_run(self, function, *args, **kwargs):
        """ register callback fired when a task is running on thread
        """
        self._on_task_run = (function, args, kwargs)

    def on_task_done(self, function, *args, **kwargs):
        """ register callback fired when a task finishes execution
        """
        self._on_task_done = (function, args, kwargs)

    def on_scheduler_start(self, function, *args, **kwargs):
        """ register callback fired when the scheduler begins execution
        """
        self._on_scheduler_start = (function, args, kwargs)

    def on_scheduler_done(self, function, *args, **kwargs):
        """ register callback fired when the scheduler completes all tasks
        """
        self._on_scheduler_done = (function, args, kwargs)
