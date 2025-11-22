from threaded_order import Scheduler
from common import runit
from progress1bar import ProgressBar

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

def start(name, pb):
    pb.alias = f'started fn {name}'

def increment(name, ok, pb):
    pb.count += 1
    pb.alias = f'completed fn {name}'

def main():

    s = Scheduler(workers=5, setup_logging=True, add_stream_handler=False)
    s.register(i01, 'i01')
    s.register(i02, 'i02')
    s.register(i03, 'i03')
    s.register(i04, 'i04')
    s.register(i05, 'i05', after=['i01'])
    s.register(i06, 'i06', after=['i01'])
    s.register(i07, 'i07', after=['i01'])
    s.register(i08, 'i08', after=['i01'])
    s.register(i09, 'i09', after=['i04'])
    s.register(i10, 'i10', after=['i04'])
    s.register(i11, 'i11', after=['i04'])
    s.register(i12, 'i12', after=['i06'])
    s.register(i13, 'i13', after=['i06'])
    s.register(i14, 'i14', after=['i06'])
    s.register(i15, 'i15', after=['i09'])
    s.register(i16, 'i16', after=['i12'])
    s.register(i17, 'i17', after=['i16'])
    with ProgressBar(total=17, clear_alias=True) as pb:
        # s.on_task_start(start, pb)
        s.on_task_done(increment, pb)
        s.start()

if __name__ == '__main__':
    main()
