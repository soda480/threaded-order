import time

class Timer:

    def __init__(self):
        self._started_wall = 0.0
        self._finished_wall = 0.0
        self._started_mono = 0.0
        self._finished_mono = 0.0

    def start(self):
        self._started_wall = time.time()
        self._started_mono = time.perf_counter()

    def stop(self):
        self._finished_wall = time.time()
        self._finished_mono = time.perf_counter()

    @property
    def duration(self):
        if self._finished_mono and self._started_mono:
            return self._finished_mono - self._started_mono
        return 0.0

    @property
    def started_at(self):
        return self._started_wall

    @property
    def finished_at(self):
        return self._finished_wall
