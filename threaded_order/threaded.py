import os
import time
import threading
import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
from .logger import configure_logging

class ThreadedOrder:
    max_workers = min(8, os.cpu_count())

    def __init__(self, workers=max_workers, setup_logging=False):
        self._workers = workers
        self._objs = {}
        self._dgraph = defaultdict(list)
        self._lock = threading.Lock()
        self._active = set()
        self._completed = threading.Event()
        self._executor = None
        self._timing = {'stime': None, 'etime': None}
        if setup_logging:
            main_thread_name = 'thread_M'
            threading.current_thread().name = main_thread_name
            configure_logging(workers, main_thread=main_thread_name)

    def _get_name(self, obj):
        if callable(obj):
            return obj.__name__
        if hasattr(obj, 'name'):
            if not hasattr(obj, 'run'):
                raise ValueError('object must have .run method that is callable')
            return obj.name
        raise ValueError('object must be callable or have .name attribute')

    def register(self, obj, after=None):
        logger = logging.getLogger(threading.current_thread().name)
        name = self._get_name(obj)
        logger.debug(f'add {name} dependent on {after}')
        if name in self._objs:
            raise ValueError(f'{name} has already been added')
        after = after or []
        unknowns = [name for name in after if name not in self._objs]
        if unknowns:
            raise ValueError(f'{name} depends on unknown {unknowns}')
        self._objs[name] = obj
        self._dgraph[name] = []
        for dname in after:
            self._dgraph[name].append(dname)
        if self._has_cycle():
            raise ValueError(f'adding {name} will create a cycle')

    def dregister(self, after=None):
        def decorator(function):
            @wraps(function)
            def wrapper(*args, **kwargs):
                return function(*args, **kwargs)
            # register at decoration time so start() can discover it
            self.register(wrapper, after=after)
            # keep a pointer to the original
            wrapper.__original__ = function
            return wrapper
        return decorator

    def _has_cycle(self):
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
        return any(visit(node) for node in self._objs)

    def _unregister(self, rname):
        logger = logging.getLogger(threading.current_thread().name)
        for name, deps in self._dgraph.items():
            if rname in deps:
                logger.debug(f'removing {rname} as a dependency from {name}')
                with self._lock:
                    self._dgraph[name].remove(rname)
        if rname in self._dgraph and not self._dgraph[rname]:
            logger.debug(f'removing {rname} from dependency graph')
            with self._lock:
                del self._dgraph[rname]

    def _get_cands(self, number):
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
        cands = [
            name for name, deps in self._dgraph.items() if not deps and name not in self._active]
        cands = cands[:number]
        logger.debug(f'requested {number} {_get_msg(cands)}')
        return cands

    def start(self):
        logger = logging.getLogger(threading.current_thread().name)
        self._timing['stime'] = time.time()
        with ThreadPoolExecutor(max_workers=self._workers, thread_name_prefix='thread') as executor:
            self._executor = executor
            logger.info(f'starting thread pool with {self._workers} threads')
            for name in self._get_cands(self._workers):
                self._submit(name)
            self._completed.wait()
            logger.info('all work completed')
        self._timing['etime'] = time.time()
        duration = self._timing['etime'] - self._timing['stime']
        logger.info(f'duration: {duration:.2f}s')

    def _submit(self, name):
        logger = logging.getLogger(threading.current_thread().name)
        logger.debug(f'submitting {name} to thread pool')
        future = self._executor.submit(self._run, name)
        logger.debug(f'adding {name} to active futures')
        with self._lock:
            self._active.add(name)
        future.add_done_callback(self._done)

    def _done(self, future):
        logger = logging.getLogger(threading.current_thread().name)
        name = future.result()
        logger.debug(f'removing {name} from active futures')
        with self._lock:
            self._active.discard(name)
        self._unregister(name)
        cands = self._get_cands(1)
        if cands:
            self._submit(cands[0])
        if not self._dgraph and not self._active:
            logger.debug('nothing more to run and no active futures remain - signaling all done')
            self._completed.set()

    def _run(self, name):
        logger = logging.getLogger(threading.current_thread().name)
        logger.debug(f'run {name}')
        if callable(self._objs[name]):
            self._objs[name]()
        else:
            self._objs[name].run()
        return name

    def __repr__(self):
        rstr = '\n'.join([f'{name}: {deps}' for name, deps in self._dgraph.items()])
        return f'Dependency Graph:\n{rstr}'
