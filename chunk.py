import io
import sys
import logging


class Chunk(object):
    def __init__(self, chash, objHash, codeObject, sourceChunk, lineno,
                 end_lineno, prevChunk):

        self.chash = chash
        self.codeObject = codeObject
        self.objHash = objHash
        self.sourceChunk = sourceChunk
        self.lineRange = range(lineno, end_lineno + 1)
        self.prevChunk = prevChunk

        self.postState = None
        self.valid = False
        self.output = None

    def update(self, sourceChunk, lineno, end_lineno):
        self.sourceChunk = sourceChunk
        self.lineRange = range(lineno, end_lineno+1)

    def execute(self):
        logging.debug('exec %s', self.getDebugId())

        assert self.prevChunk
        assert self.prevChunk.valid
        self.postState = dict(self.prevChunk.postState)

        stdoutBuffer = io.StringIO()
        prev_stdout, sys.stdout = sys.stdout, stdoutBuffer
        self.postState['sys'] = sys

        self.output = None

        try:
            exec(self.codeObject, self.postState)
        except Exception as e:
            self.output = repr(e) + stdoutBuffer.getvalue().strip()
            self.valid = False
        else:
            self.output = stdoutBuffer.getvalue().strip()
            self.valid = True

        sys.stdout = prev_stdout

        return self.valid

    def getDebugId(self):
        return f'{self.lineRange.start}: {self.sourceChunk.splitlines()[0]}'

class DummyInitialChunk(Chunk):
    def __init__(self, initialNamespace):
        super().__init__(0, 0, None, None, 0, 0, None)
        self.postState = initialNamespace
        self.valid = True

