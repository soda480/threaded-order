from threaded import Threaded
from common import runit

workers = 5
threaded = Threaded(workers=workers)

@threaded.dregister()
def i01():
    runit(i01.__name__)

@threaded.dregister()
def i02():
    runit(i02.__name__)

@threaded.dregister()
def i03():
    runit(i03.__name__)

@threaded.dregister()
def i04():
    runit(i04.__name__)

@threaded.dregister(after=['i01'])
def i05():
    runit(i05.__name__)

@threaded.dregister(after=['i01'])
def i06():
    runit(i06.__name__)

@threaded.dregister(after=['i01'])
def i07():
    runit(i07.__name__)

@threaded.dregister(after=['i01'])
def i08():
    runit(i08.__name__)

@threaded.dregister(after=['i04'])
def i09():
    runit(i09.__name__)

@threaded.dregister(after=['i04'])
def i10():
    runit(i10.__name__)

@threaded.dregister(after=['i04'])
def i11():
    runit(i11.__name__)

@threaded.dregister(after=['i06'])
def i12():
    runit(i12.__name__)

@threaded.dregister(after=['i06'])
def i13():
    runit(i13.__name__)

@threaded.dregister(after=['i06'])
def i14():
    runit(i14.__name__)

@threaded.dregister(after=['i09'])
def i15():
    runit(i15.__name__)

@threaded.dregister(after=['i12'])
def i16():
    runit(i16.__name__)

@threaded.dregister(after=['i16'])
def i17():
    runit(i17.__name__)

if __name__ == '__main__':
    threaded.start()
