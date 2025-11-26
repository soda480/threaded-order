import random
import time
from threaded_order import ThreadProxyLogger

logger = ThreadProxyLogger()

def runit(name):
    sleep = random.uniform(.5, 3.5)
    logger.debug(f'{name} running - sleeping {sleep:.2f}s')
    time.sleep(sleep)
    logger.info(f'{name} PASSED')
