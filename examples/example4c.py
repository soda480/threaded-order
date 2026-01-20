import time
import random
from faker import Faker
from threaded_order import mark, ThreadProxyLogger

logger = ThreadProxyLogger()

def setup_state(state):
    state.update({'faker': Faker()})

def run(name, state, deps=None, fail=False):
    with state['_state_lock']:
        last_name = state['faker'].last_name()
    sleep = random.uniform(.5, 2.5)
    logger.debug(f'{name} \"{last_name}\" running - sleeping {sleep:.2f}s')
    time.sleep(sleep)
    if fail:
        assert False, 'Intentional Failure'
    else:
        results = []
        for dep in (deps or []):
            dep_result = state['results'].get(dep, '--no-result--')
            results.append(f'{name}.{dep_result}')
        if not results:
            results.append(name)
        logger.debug(f'{name} PASSED')
        return '|'.join(results)

@mark()
def task_a(state): return run('task_a', state)

@mark(after=['task_a'])
def task_b(state): return run('task_b', state, deps=['task_a'])

@mark(after=['task_a'])
def task_c(state): return run('task_c', state, deps=['task_a'])

@mark(after=['task_c'])
def task_d(state): return run('task_d', state, deps=['task_c'], fail=True)
    
@mark(after=['task_c'])
def task_e(state): return run('task_e', state, deps=['task_c'])

@mark(after=['task_b', 'task_d'])
def task_f(state): return run('task_f', state, deps=['task_b', 'task_d'])
