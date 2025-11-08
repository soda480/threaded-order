import threading
import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from functools import wraps

logger = logging.getLogger(__name__)
threading.current_thread().rname = 'thread_M'

class Threaded:

    def __init__(self, workers=4):
        self._workers = workers
        self._objs = {}
        self._dgraph = defaultdict(list)
        self._lock = threading.Lock()
        self._active = set()
        self._completed = threading.Event()
        self._executor = None

    def _get_name(self, obj):
        if isinstance(obj, str):
            return obj
        if callable(obj):
            return obj.__name__
        if hasattr(obj, 'name'):
            return obj.name
        raise ValueError(f'object must be callable or have .name attribute')

    def register(self, obj, after=None):
        name = self._get_name(obj)
        logger.debug(f'add {name} dependent on {after}')
        if name in self._objs:
            raise ValueError(f'{name} has already been added')
        after = after or []
        unknowns = [self._get_name(name) for name in after if self._get_name(name) not in self._objs]
        if unknowns:
            raise ValueError(f'{name} depends on unknown {unknowns}')
        self._objs[name] = obj
        self._dgraph[name] = []
        for dname in after:
            self._dgraph[name].append(self._get_name(dname))
        if self._has_cycle():
            raise ValueError(f'adding {name} will create a cycle')
    
    def _has_cycle(self):
        pass

    def _unregister(self, rname):
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
        cands = [
            name for name, deps in self._dgraph.items()
                if not deps and name not in self._active]
        cands = cands[:number]
        logger.debug(f'requested {number} {_get_msg(cands)}')
        return cands

    def start(self):
        with ThreadPoolExecutor(max_workers=self._workers, thread_name_prefix='thread') as executor:
            self._executor = executor
            logger.info(f'starting thread pool with {self._workers} threads')
            for name in self._get_cands(self._workers):
                self._submit(name)
            self._completed.wait()
            logger.info('all work completed')
    
    def _submit(self, name):
        logger.debug(f'submitting {name} to thread pool')
        future = self._executor.submit(self._run, name)
        logger.debug(f'adding {name} to active futures')
        with self._lock:
            self._active.add(name)
        future.add_done_callback(self._done)

    def _done(self, future):
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
        logger.debug(f'run {name}')
        if callable(self._objs[name]):
            self._objs[name]()
        else:
            self._objs[name].run()
        return name
    
    def __repr__(self):
        rstr = '\n'.join([f'{name}: {deps}' for name, deps in self._dgraph.items()])
        return f'Dependency Graph:\n{rstr}'
