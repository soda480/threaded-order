import random
import time
import threading
import logging

def runit(name):
    logger = logging.getLogger(threading.current_thread().name)
    sleep = random.uniform(3, 12)
    logger.debug(f'{name} running - sleeping {sleep:.2f}s')
    time.sleep(sleep)
    logger.info(f'{name} completed')
