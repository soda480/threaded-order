from threaded_order import Scheduler
from common import runit

def main():
    s = Scheduler(workers=5, setup_logging=True)
    s.register(lambda: runit('i01'), 'i01')
    s.register(lambda: runit('i02'), 'i02')
    s.register(lambda: runit('i03'), 'i03')
    s.register(lambda: runit('i04'), 'i04')
    s.register(lambda: runit('i05'), 'i05', after=['i01'])
    s.register(lambda: runit('i06'), 'i06', after=['i01'])
    s.register(lambda: runit('i07'), 'i07', after=['i01'])
    s.register(lambda: runit('i08'), 'i08', after=['i01'])
    s.register(lambda: runit('i09'), 'i09', after=['i04'])
    s.register(lambda: runit('i10'), 'i10', after=['i04'])
    s.register(lambda: runit('i11'), 'i11', after=['i04'])
    s.register(lambda: runit('i12'), 'i12', after=['i06'])
    s.register(lambda: runit('i13'), 'i13', after=['i06'])
    s.register(lambda: runit('i14'), 'i14', after=['i06'])
    s.register(lambda: runit('i15'), 'i15', after=['i09'])
    s.register(lambda: runit('i16'), 'i16', after=['i12'])
    s.register(lambda: runit('i17'), 'i17', after=['i16'])
    s.start()

if __name__ == '__main__':
    main()
