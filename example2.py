from threaded import Threaded
from common import runit

class Item():
    def __init__(self, name):
        self.name = name
    def run(self):
        runit(self.name)
    def __repr__(self):
        return f'Item({self.name})'

def main():
    threaded = Threaded(workers=5)
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

    threaded.start()

if __name__ == '__main__':
    main()
