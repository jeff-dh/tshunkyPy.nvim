from contextlib import contextmanager
from threading import Lock

def createBuffer(nvim, listed=True, scratch=False, **kwargs):
    buf = nvim.api.create_buf(listed, scratch)
    if 'name' in kwargs.keys():
        buf.name = kwargs['name']
        del kwargs['name']
    for k, v in kwargs.items():
        buf.api.set_option(k, v)

    return buf

@contextmanager
def modifiable(buf):
    buf.api.set_option('modifiable', True)
    yield
    buf.api.set_option('modifiable', False)

class NvimLock:
    def __init__(self, nvim):
        self.nvim = nvim
        self.lock = Lock()

    def __enter__(self):
        while not self.lock.acquire(blocking=False):
            #noop as yield, couldn't find any better solution....
            self.nvim.api.command('')

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.lock.release()

