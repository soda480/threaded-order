from threaded_order import Scheduler, ThreadProxyLogger
import time
import json
import random

s = Scheduler(workers=3, setup_logging=True)
logger = ThreadProxyLogger()

def run(name, fail=False):
    sleep = random.uniform(.5, 3.5)
    time.sleep(sleep)
    if fail:
        assert False, "Intentional Failure"
    else:
        logger.info(f'{name}: PASSED')
    return sleep

@s.dregister(with_state=True)
def test_a(state): return run('test_a')

@s.dregister(with_state=True, after=['test_a'])
def test_b(state): return run('test_b')

@s.dregister(with_state=True, after=['test_a'])
def test_c(state): return run('test_c')

@s.dregister(with_state=True, after=['test_c'])
def test_d(state): return run('test_d', fail=True)

@s.dregister(after=['test_c'])
def test_e(): return run('test_e')

@s.dregister(with_state=True, after=['test_b', 'test_d'])
def test_f(state): return run('test_f')

if __name__ == '__main__':
    s.on_scheduler_done(lambda s: print(f"Passed:{len(s['passed'])} Failed:{len(s['failed'])}"))
    s.start()
    print(json.dumps(s.state, indent=2, default=str))