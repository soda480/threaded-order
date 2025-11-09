from threaded import Threaded
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
    runit(i06.__name__)

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
    threaded = Threaded(workers=5)
    threaded.register(i01)
    threaded.register(i02)
    threaded.register(i03)
    threaded.register(i04)
    threaded.register(i05, after=['i01'])
    threaded.register(i06, after=['i01'])
    threaded.register(i07, after=['i01'])
    threaded.register(i08, after=['i01'])
    threaded.register(i09, after=['i04'])
    threaded.register(i10, after=['i04'])
    threaded.register(i11, after=['i04'])
    threaded.register(i12, after=['i06'])
    threaded.register(i13, after=['i06'])
    threaded.register(i14, after=['i06'])
    threaded.register(i15, after=['i09'])
    threaded.register(i16, after=['i12'])
    threaded.register(i17, after=['i16'])
    threaded.start()

if __name__ == '__main__':
    main()
