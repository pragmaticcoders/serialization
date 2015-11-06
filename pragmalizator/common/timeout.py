from pragmalizator.common import time


class Mixin(object):

    _timeouts = None # {TIMEOUT_NAME: (TIMEOUT, CALLBACK)}
    _callids = None # {TIMEOUT_NAME: IDelayedCall}

    def add_timeout(self, name, duration, callback):
        self._lazy_setup()
        self._timeouts[name] = (duration, callback)

    def reset_timeout(self, name):
        assert name in self._timeouts, "Unknown timeout " + name
        self.cancel_timeout(name)
        duration = self._timeouts[name][0]
        dc = time.call_later(duration, self._on_timeout, name)
        self._callids[name] = dc

    def cancel_timeout(self, name):
        assert name in self._timeouts, "Unknown timeout " + name
        if name in self._callids:
            dc = self._callids.pop(name)
            dc.cancel()

    def cancel_all_timeouts(self):
        if self._timeouts is None:
            return
        for dc in self._callids.values():
            dc.cancel()
        self._callids.clear()

    def _lazy_setup(self):
        if self._timeouts is None:
            self._timeouts = {}
            self._callids = {}

    def _on_timeout(self, name):
        del self._callids[name]
        self._timeouts[name][1]()
