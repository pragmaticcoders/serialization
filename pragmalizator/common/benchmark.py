import time

from pragmalizator.common import log


class Benchmark(log.Logger):

    log_category = 'benchmark'

    def __init__(self, log_keeper):
        log.Logger.__init__(self, log_keeper)
        self._last = None

    def report(self, *what):
        t = time.time()
        if self._last is None:
            self._last = t
            self._start = t
        delta = t - self._last
        self._last = t
        from_start = t - self._start
        self.info("%f %f " + what[0], from_start, delta, *what[1:])


benchmark = Benchmark(log.get_default())
