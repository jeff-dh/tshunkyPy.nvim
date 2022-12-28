from ...chunk import Chunk

class LuaChunk(Chunk):
    def __init__(self, node, sourceChunk, filename, prevChunk,
                 outputManager=None):
        self._lineRange, _ = node
        super().__init__(sourceChunk, prevChunk, outputManager)
        self.filename = filename

    @property
    def lineRange(self):
        return self._lineRange

    def update(self, node):
        self._lineRange, _ = node

    def execute_impl(self):

        return True

