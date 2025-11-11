from threaded_order import ThreadedOrder, ThreadProxyLogger
from time import sleep

to = ThreadedOrder(workers=3, setup_logging=True)
logger = ThreadProxyLogger()

@to.dregister()
def a(): sleep(1); logger.info("a")

@to.dregister(after=['a'])
def b(): sleep(1); logger.info("b")

@to.dregister(after=['a'])
def c(): sleep(1); logger.info("c")

@to.dregister(after=['b', 'c'])
def d(): sleep(1); logger.info("d")

if __name__ == '__main__':
    to.on_scheduler_done(lambda s: print(f"Passed:{len(s['passed'])} Failed:{len(s['failed'])}"))
    to.start()
