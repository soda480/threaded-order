from threaded_order import dmark, ThreadProxyLogger
import time
import random

logger = ThreadProxyLogger()

STATE = {
    'k1': 'v1',
    'k2': 'v2',
}

def run(name, fail=False):
    sleep = random.uniform(.5, 3.5)
    time.sleep(sleep)
    if fail:
        assert False, "Intentional Failure"
    else:
        logger.info(f'{name}: passed')
    return sleep

@dmark(with_state=True)
def test_a(state): return run('test_a')

@dmark(with_state=True, after=['test_a'])
def test_b(state): return run('test_b')

@dmark(with_state=True, after=['test_a'])
def test_c(state): return run('test_c')

@dmark(with_state=True, after=['test_c'])
def test_d(state): return run('test_d', fail=True)

@dmark(after=['test_c'])
def test_e(): return run('test_e')

@dmark(with_state=True, after=['test_b', 'test_d'])
def test_f(state): return run('test_f')
