from threaded_order import Scheduler, ThreadProxyLogger
from time import sleep

s = Scheduler(workers=3, setup_logging=True)
logger = ThreadProxyLogger()

@s.dregister()
def a(): sleep(1); logger.info("a")

@s.dregister(after=['a'])
def b(): sleep(1); logger.info("b")

@s.dregister(after=['a'])
def c(): sleep(1); logger.info("c")

@s.dregister(after=['b', 'c'])
def d(): sleep(1); logger.info("d")

if __name__ == '__main__':
    s.on_scheduler_done(lambda s: print(f"Passed:{len(s['passed'])} Failed:{len(s['failed'])}"))
    s.start()
