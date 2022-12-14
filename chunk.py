import logging


class DummyInitialChunk(object):
    def __init__(self, initialNamespace):
        self.postState = initialNamespace
        self.chash = 0
        self.valid = True

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

    def update(self, sourceChunk, lineno, end_lineno):
        self.sourceChunk = sourceChunk
        self.lineno = lineno
        self.end_lineno = end_lineno

    def execute(self):
        logging.debug('exec %s', self.getDebugId())

        assert self.prevChunk
        # assert self.prevChunk.valid
        self.postState = dict(self.prevChunk.postState)

        try:
            exec(self.codeObject, self.postState)
        except Exception:
            import traceback
            print(traceback.format_exc())
            if not self.prevChunk.valid:
                print("At least one previous chunks is not valid..... is " +
                      "that maybe the reason for this exception?")
            return False

        self.valid = True

        return True

    def getDebugId(self):
        return f'{self.lineRange.start}: {self.sourceChunk.splitlines()[0]}'

