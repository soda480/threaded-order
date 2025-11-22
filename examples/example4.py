from threaded_order import Scheduler, ThreadProxyLogger
import time
import random

s = Scheduler(workers=3, setup_logging=True)
logger = ThreadProxyLogger()

def run(name):
    time.sleep(random.uniform(.5, 3.5))
    logger.info(f'{name} completed')

@s.dregister()
def a(): run('a')

@s.dregister(after=['a'])
def b(): run('b')

@s.dregister(after=['a'])
def c(): run('c')

@s.dregister(after=['c'])
def d(): run('d')

@s.dregister(after=['c'])
def e(): run('e')

@s.dregister(after=['b', 'd'])
def f(): run('f')

if __name__ == '__main__':
    s.on_scheduler_done(lambda s: print(f"Passed:{len(s['passed'])} Failed:{len(s['failed'])}"))
    s.start()
