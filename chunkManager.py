import ast
import logging

from .utils import ExprPrintWrapper
from .chunk import Chunk, DummyInitialChunk


class ChunkManager(object):
    def __init__(self):
        self.chunkList = []
        self.chunks = {}

        self.error = None

    def _parseSource(self, source):
        try:
            module_ast = ast.parse(source)
        except SyntaxError as e:
            self.error = e
            errorChunk = self._getChunkByLine(e.lineno)
            if errorChunk:
                idx = self.chunkList.index(errorChunk.chash)
                for chash in self.chunkList[idx:]:
                    c = self.chunks[chash]
                    c.valid = False
                    c.stdout = ''
                    c.vtexts = []
            return None

        # wrap every expression statement into a print call
        return ExprPrintWrapper().visit(module_ast)


    def update(self, source, filename='<string>'):
        #we request an update when the last state was an error state
        needsUpdate = not self.error is None
        self.error = None

        module_ast = self._parseSource(source)
        if not module_ast:
            return -1

        #reset chunkList
        self.chunkList = []
        prevChunk = DummyInitialChunk({})

        for n in module_ast.body:
            # calculate chunk hash
            src = ast.get_source_segment(source, n)
            chash = f'{prevChunk.chash}{len(self.chunkList)}{src}'.__hash__()
            self.chunkList.append(chash)

            # update chunk or create new one
            if chash in self.chunks:
                # chunk (and it predecessors) did not change
                # there might have been a whitespace change
                chunk = self.chunks[chash]
                chunk.update(n.lineno, n.end_lineno)
            else:
                # chunk or a predecessor changed
                # create new chunk
                chunk = Chunk(chash, n, src, filename, prevChunk)
                self.chunks[chash] = chunk

                logging.debug('changed %s', self.chunks[chash].getDebugId())
                needsUpdate = True

            prevChunk = chunk

        if self._cleanUpCaches():
            needsUpdate = True
        return needsUpdate


    def executeAllChunks(self):
        if self.error:
            return False
        for chunk in self._getOrderedChunks():
            if not chunk.execute():
                return False

        return True

    def executeAllInvalidChunks(self):
        if self.error:
            return False
        for chunk in self._getOrderedChunks():
            if not chunk.valid:
                if not chunk.execute():
                    return False
        return True

    def executeFirstInvalidChunk(self):
        if self.error:
            return False
        for chunk in self._getOrderedChunks():
            if not chunk.valid:
                return chunk.execute()

        return False

    def getInvalidChunkRanges(self):
        ranges = []
        for chunk in self._getOrderedChunks():
            if not chunk.valid:
                ranges.append(chunk.lineRange)

        if self.error:
            chunk = self._getChunkByLine(self.error.lineno)
            if chunk:
                ranges.append(chunk.lineRange)

        return ranges

    def getVTexts(self):
        vtexts = []

        for chash in self.chunkList:
            c = self.chunks[chash]
            vtexts.extend(c.vtexts)

        if self.error:
            vtexts.append((self.error.lineno, repr(self.error)))

        return  vtexts

    def getStdout(self):
        if self.error:
            return repr(self.error)

        outList = [c.stdout for c in self._getOrderedChunks() if c.stdout]
        return ''.join(outList)

    def _getOrderedChunks(self):
        return [self.chunks[chash] for chash in self.chunkList]

    def _getChunkByLine(self, line):
        for chunk in self.chunks.values():
            if line in chunk.lineRange:
                return chunk
        return None

    def _cleanUpCaches(self):
        changed = False
        chunksSet = set(self.chunks.keys())
        listSet = set(self.chunkList)
        for chash in chunksSet - listSet:
            logging.debug("deleted %s", self.chunks[chash].getDebugId())
            changed = True

            assert chash not in self.chunkList
            del self.chunks[chash]

        assert len(self.chunks) == len(self.chunkList)

        return changed

