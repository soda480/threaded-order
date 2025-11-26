import time
import random
import threading
from faker import Faker
from threaded_order import dmark, ThreadProxyLogger

logger = ThreadProxyLogger()

def setup_state(**kwargs):
    state = {
        'faker': Faker(),
        'faker_lock': threading.RLock(),
        'results': {},
    }
    for key, value in kwargs.items():
        if key.startswith('result-'):
            test_name = key[len('result-'):]
            state['results'][test_name] = value
        else:
            state[key] = value
    return state

def run(name, state, deps=None, fail=False):
    with state['faker_lock']:
        faker = state['faker']
        last_name = faker.last_name()
    sleep = random.uniform(.5, 3.5)
    logger.debug(f'{name} {last_name} running - sleeping {sleep:.2f}s')
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
        logger.info(f'{name} passed')
        return '|'.join(results)

@dmark(with_state=True)
def test_a(state): return run('test_a', state)

@dmark(with_state=True, after=['test_a'])
def test_b(state): return run('test_b', state, deps=['test_a'])

@dmark(with_state=True, after=['test_a'])
def test_c(state): return run('test_c', state, deps=['test_a'])

@dmark(with_state=True, after=['test_c'])
def test_d(state): return run('test_d', state, deps=['test_c'], fail=True)
    
@dmark(with_state=True, after=['test_c'])
def test_e(state): return run('test_e', state, deps=['test_c'])

@dmark(with_state=True, after=['test_b', 'test_d'])
def test_f(state): return run('test_f', state, deps=['test_b', 'test_d'])
