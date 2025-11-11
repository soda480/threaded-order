import json
from threaded_order import ThreadedOrder
from common import runit

def i01():
    runit(i01.__name__)

def i02():
    runit(i02.__name__)

def i03():
    runit(i03.__name__)

def i04():
    runit(i04.__name__)

def i05():
    runit(i05.__name__)

def i06():
    # runit(i06.__name__)
    raise Exception('error with i06')

def i07():
    runit(i07.__name__)

def i08():
    runit(i08.__name__)

def i09():
    runit(i09.__name__)

def i10():
    runit(i10.__name__)

def i11():
    runit(i11.__name__)

def i12():
    runit(i12.__name__)

def i13():
    runit(i13.__name__)

def i14():
    runit(i14.__name__)

def i15():
    runit(i15.__name__)

def i16():
    runit(i16.__name__)

def i17():
    runit(i17.__name__)

def main():
    threaded = ThreadedOrder(workers=5, setup_logging=True, add_stream_handler=False)
    threaded.on_task_start(lambda n: print("[start]", n))
    threaded.on_task_done(lambda n, ok: print("[done ]", n, ok))
    threaded.on_scheduler_start(lambda info: print(f"Starting {info['total_tasks']} tasks across a {info['workers']} pool"))
    threaded.on_scheduler_done(lambda s: print(json.dumps(s, indent=2)))
    threaded.register(i01, 'i01')
    threaded.register(i02, 'i02')
    threaded.register(i03, 'i03')
    threaded.register(i04, 'i04')
    threaded.register(i05, 'i05', after=['i01'])
    threaded.register(i06, 'i06', after=['i01'])
    threaded.register(i07, 'i07', after=['i01'])
    threaded.register(i08, 'i08', after=['i01'])
    threaded.register(i09, 'i09', after=['i04'])
    threaded.register(i10, 'i10', after=['i04'])
    threaded.register(i11, 'i11', after=['i04'])
    threaded.register(i12, 'i12', after=['i06'])
    threaded.register(i13, 'i13', after=['i06'])
    threaded.register(i14, 'i14', after=['i06'])
    threaded.register(i15, 'i15', after=['i09'])
    threaded.register(i16, 'i16', after=['i12'])
    threaded.register(i17, 'i17', after=['i16'])
    # print(threaded)
    threaded.start()

if __name__ == '__main__':
    main()
