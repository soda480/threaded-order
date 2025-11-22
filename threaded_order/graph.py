import threading
import logging
from collections import defaultdict

def log_candidates(candidates, number):
    """ log a debug message describing how many candidate nodes were found
    """
    logger = logging.getLogger(threading.current_thread().name)
    count = len(candidates)
    if not candidates:
        message = 'but found no candidates eligible for submission'
    else:
        base = f"and found {count} candidate{'s' if count != 1 else ''} eligible for submission"
        message = f"{base} {', '.join(candidates)}"
    logger.debug(f'requested {number} {message}')

class DAGraph:

    def __init__(self):
        """ initialize an empty DAG with parent and child adjacency mappings
        """
        self._parents = defaultdict(list)
        self._children = defaultdict(set)

    def add(self, name, after=None):
        """ add a new node with optional dependencies

            All items in `after` must already exist in the DAG.
            Raises ValueError if the node already exists, dependencies are unknown,
            or the addition would introduce a cycle.
        """
        logger = logging.getLogger(threading.current_thread().name)
        after = after or []
        logger.debug(f'add {name} dependent on {after}')
        if name in self._parents:
            raise ValueError(f'{name} has already been added')
        unknowns = [dep for dep in after if dep not in self._parents]
        if unknowns:
            raise ValueError(f'{name} depends on unknown {unknowns}')
        self._parents[name] = []
        for dep in after:
            self._parents[name].append(dep)
            self._children[dep].add(name)
        if self._has_cycle():
            # rollback this node to keep DAG consistent
            for dep in after:
                self._children[dep].discard(name)
            self._parents.pop(name, None)
            raise ValueError(f'adding {name} will create a cycle')

    def remove(self, name):
        """ remove a completed node and detach it from all dependent children

            Cleans up parent and child relationships and drops the node completely
            once it has no remaining edges.
        """
        logger = logging.getLogger(threading.current_thread().name)
        for child in self._children.pop(name, ()):
            logger.debug(f'removing {name} as a dependency from {child}')
            try:
                self._parents[child].remove(name)
            except ValueError:
                # defensive: graph might already be partially cleaned
                pass

        if name in self._parents and not self._parents[name]:
            logger.debug(f'removing {name} from dependency graph')
            self._parents.pop(name, None)

    def ready(self, active=None):
        """ return a list of nodes whose dependencies are satisfied and not active
        """
        if active is None:
            active = set()
        return [name for name, deps in self._parents.items() if not deps and name not in active]

    def get_candidates(self, active, number, sort=True):
        """ return up to `number` ready nodes, optionally sorted for stable scheduling

            Also logs the candidate list for visibility.
        """
        candidates = self.ready(active)
        if sort:
            candidates = sorted(candidates)
        log_candidates(candidates, number)
        return candidates[:number]

    def _has_cycle(self):
        """ return True if DAGraph contains a cycle
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
            for neighbor in self._parents[node]:
                if visit(neighbor):
                    return True
            stack.remove(node)
            return False
        return any(visit(node) for node in self._parents)

    def is_empty(self):
        """ return True if the DAGraph has no nodes
        """
        return not self._parents and not self._children

    def __repr__(self):
        """ return a human-readable representation of the dependency graph
        """
        parents = '\n'.join(f'{n}: {self._parents[n]}' for n in sorted(self._parents))
        children = '\n'.join(
            f'{n}: {sorted(list(self._children[n]))}' for n in sorted(self._children))
        return f'Parents:\n{parents}\nChildren:\n{children}'
