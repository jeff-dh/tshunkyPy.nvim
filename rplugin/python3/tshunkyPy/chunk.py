
import logging

class Chunk(object):
    def __init__(self, sourceChunk, prevChunk, outputManager=None):

        self.sourceChunk = sourceChunk
        self.prevChunk = prevChunk
        self.outputManager = outputManager

        # defines valid, stdout and vtexts
        self.reset()

    def reset(self):
        self._valid, self.stdout, self.vtexts = False, None, {}
        if self.outputManager:
            self.outputManager.update(self)

    @property
    def valid(self):
        return self._valid

    @property
    def lineRange(self):
        raise NotImplemented

    def update(self, _):
        raise NotImplemented

    def cleanup(self):
        assert self.outputManager
        self.outputManager.delete(self)

    def execute_impl(self):
        raise NotImplemented

    def execute(self):
        logging.debug('exec %s', self.getDebugId())

        assert self.prevChunk
        assert self.prevChunk._valid

        self._valid = self.execute_impl()

        assert self.outputManager
        self.outputManager.update(self)

        return self._valid

    def getDebugId(self):
        return f'{self.lineRange.start}: {self.sourceChunk.splitlines()[0]}'

class DummyInitialChunk(Chunk):
    def __init__(self, initialNamespace):
        super().__init__(None, None, None)
        self.namespace = initialNamespace
        self._valid = True
