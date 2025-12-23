import time
import random
from faker import Faker
from threaded_order import mark, configure_logging, ThreadProxyLogger

logger = ThreadProxyLogger()

def setup_state(state):
    state.update({
        'faker': Faker()
    })

def setup_logging(workers, verbose):
    configure_logging(workers, prefix='thread', add_stream_handler=True, verbose=verbose)

def run(name, state, deps=None, fail=False):
    with state['_state_lock']:
        last_name = state['faker'].last_name()
    sleep = random.uniform(.5, 3.5)
    logger.debug(f'{name} \"{last_name}\" running - sleeping {sleep:.2f}s')
    time.sleep(sleep)
    if fail:
        assert False, 'Intentional Failure'
    else:
        results = []
        for dep in (deps or []):
            dep_result = state.get(dep, '--no-result--')
            results.append(f'{name}.{dep_result}')
        if not results:
            results.append(name)
        logger.info(f'{name} PASSED')
        state[name] = '|'.join(results)

@mark(tags='layer1')
def test_a(state): return run('test_a', state)

@mark(tags='layer1')
def test_z(state): return run('test_z', state)

@mark(after=['test_a', 'test_z'], tags='layer2')
def test_b(state): return run('test_b', state, deps=['test_a'])

@mark(after=['test_a'], tags='layer2')
def test_c(state): return run('test_c', state, deps=['test_a'])

@mark(after=['test_c'], tags='layer3')
def test_d(state): return run('test_d', state, deps=['test_c'], fail=True)
    
@mark(after=['test_c'], tags='layer3')
def test_e(state): return run('test_e', state, deps=['test_c'])

@mark(after=['test_b', 'test_d'], tags='layer4')
def test_f(state): return run('test_f', state, deps=['test_b', 'test_d'])

