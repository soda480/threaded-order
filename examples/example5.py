from threaded_order import Scheduler
from common import runit
from progress1bar import ProgressBar

def task_done(name, _, pb):
    pb.count += 1
    pb.alias = f'Completed {name}'

def scheduler_done(summary, pb):
    pb.alias = f"Passed:{len(summary['passed'])} Failed:{len(summary['failed'])}"

def main():
    s = Scheduler(workers=5)
    s.register(lambda: runit('a'), 'a')
    s.register(lambda: runit('b'), 'b', after=['a'])
    s.register(lambda: runit('c'), 'c', after=['a'])
    s.register(lambda: runit('d'), 'd', after=['c'])
    s.register(lambda: runit('e'), 'e', after=['c'])
    s.register(lambda: runit('f'), 'f', after=['b', 'd'])
    with ProgressBar(total=6, show_complete=False) as pb:
        s.on_task_done(task_done, pb)
        s.on_scheduler_done(scheduler_done, pb)
        s.start()

if __name__ == '__main__':
    main()
