import sys
import random
import time
import logging
from threaded import Threaded

logger = logging.getLogger(__name__)

def configure_logging(level=logging.DEBUG):
    rlogger = logging.getLogger()
    rlogger.setLevel(level)

    shandler = logging.StreamHandler(stream=sys.stderr)
    sformatter = logging.Formatter("%(asctime)s %(threadName)s %(levelname)s [%(funcName)s]: %(message)s")
    shandler.setFormatter(sformatter)
    shandler.setLevel(level)
    rlogger.addHandler(shandler)

def runit(name):
    sleep = random.uniform(3, 12)
    logger.debug(f'{name} running - sleeping {sleep:.2f}s')
    time.sleep(sleep)
    logger.info(f'{name} completed')

class Item():
    def __init__(self, name):
        self.name = name
    def run(self):
        runit(self.name)
    def __repr__(self):
        return f'Item({self.name})'

def main():
    threaded = Threaded(workers=4)
    threaded.register(Item('i01'))
    threaded.register(Item('i02'))
    threaded.register(Item('i03'))
    threaded.register(Item('i04'))
    threaded.register(Item('i05'), after=['i01'])
    threaded.register(Item('i06'), after=['i01'])
    threaded.register(Item('i07'), after=['i01'])
    threaded.register(Item('i08'), after=['i01'])
    threaded.register(Item('i09'), after=['i04'])
    threaded.register(Item('i10'), after=['i04'])
    threaded.register(Item('i11'), after=['i04'])
    threaded.register(Item('i12'), after=['i06'])
    threaded.register(Item('i13'), after=['i06'])
    threaded.register(Item('i14'), after=['i06'])
    threaded.register(Item('i15'), after=['i09'])
    threaded.register(Item('i16'), after=['i12'])
    threaded.register(Item('i17'), after=['i16'])

    stime = time.time()
    threaded.start()
    etime = time.time()
    duration = etime - stime
    print(f'duration: {duration:.2f}s')

if __name__ == '__main__':
    configure_logging()
    main()
