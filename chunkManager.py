import ast
import logging
import pprint

from .utils import ExprPrintWrapper
from .chunk import Chunk, DummyInitialChunk


def patchedPrint(*args, **kwargs):
    if args and args[0] is None:
        return
    else:
        if not isinstance(args[0], str):
            pprint.pprint(*args, **kwargs, indent=4)
        else:
            print(*args, **kwargs)

class ChunkManager(object):
    def __init__(self):
        self.chunkList = []

        self.objCache = {}
        self.chunks = {}

        initialNamespace = {'print': patchedPrint}
        self.dummyInitialChunk = DummyInitialChunk(initialNamespace)
        self.error = None


    def _parseSource(self, source):
        try:
            module_ast = ast.parse(source)
        except SyntaxError as e:
            self.error = e
            errorChunk = self._getChunkByLine(e.lineno)
            if errorChunk:
                errorChunk.valid = False
                errorChunk.output = ''
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
        prevChunk = self.dummyInitialChunk

        for n in module_ast.body:
            # calculate (code) object hash
            sourceChunk = ast.get_source_segment(source, n)
            assert sourceChunk
            objHash = sourceChunk.__hash__()

            # calculate chunk hash
            prevHash = prevChunk.chash
            chash = (objHash + prevHash).__hash__()
            self.chunkList.append(chash)

            # compile code object
            self._updateObjCache(n, objHash, filename)

            # update chunk or create new one
            if chash in self.chunks:
                # chunk (and it predecessors) did not change
                # there might have been a whitespace change
                chunk = self.chunks[chash]
                chunk.update(sourceChunk, n.lineno, n.end_lineno)
            else:
                # chunk or a predecessor changed
                # create new chunk
                chunk = Chunk(chash, objHash, self.objCache[objHash],
                              sourceChunk, n.lineno, n.end_lineno, prevChunk)
                self.chunks[chash] = chunk

                logging.debug('changed %s', self.chunks[chash].getDebugId())
                needsUpdate = True

            prevChunk = chunk

        if self._cleanUpCaches():
            needsUpdate = True
        return needsUpdate


    def executeAllChunks(self):
        for chunk in self._getOrderedChunks():
            if not chunk.execute():
                return False

        return True

    def executeAllInvalidChunks(self):
        for chunk in self._getOrderedChunks():
            if not chunk.valid:
                if not chunk.execute():
                    return False
        return True

    def executeFirstInvalidChunk(self):
        for chunk in self._getOrderedChunks():
            if not chunk.valid:
                return chunk.execute()

        return False

    def executeChunkByLine(self, line):
        chunk = self._getChunkByLine(line)
        if chunk:
            return chunk.execute()

        return False

    def executeChunksByRange(self, start, end):
        rangeSet = set(range(start, end+1))

        for chunk in self._getOrderedChunks():
            if len(rangeSet.intersection(chunk.lineRange)):
                if not chunk.execute():
                    return False

        return True

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

    def getOutput(self):
        outputList = [(c.lineRange.stop-1, c.output, False)
                      for c in self.chunks.values() if c.output]

        errorList = [(self.error.lineno, repr(self.error), True)]  \
                        if self.error else []

        return  outputList + errorList

    def _getOrderedChunks(self):
        return [self.chunks[chash] for chash in self.chunkList]

    def _getChunkByLine(self, line):
        for chunk in self.chunks.values():
            if line in chunk.lineRange:
                return chunk
        return None

    def _updateObjCache(self, node, objHash, filename):
        if objHash in self.objCache.keys():
            return

        wrapperModule = ast.Module(body=[node], type_ignores=[])
        self.objCache[objHash] = compile(wrapperModule, filename, 'exec')

    def _cleanUpCaches(self):
        changed = False
        chunksSet = set(self.chunks.keys())
        listSet = set(self.chunkList)
        for chash in chunksSet - listSet:
            logging.debug("deleted %s", self.chunks[chash].getDebugId())
            changed = True

            assert chash not in self.chunkList
            del self.chunks[chash]

        objSet = set(c.objHash for c in self.chunks.values())
        objCacheSet = set(self.objCache.keys())
        for objHash in objCacheSet - objSet:
            del self.objCache[objHash]

        assert len(self.chunks) == len(self.chunkList)
        assert len(self.objCache) <= len(self.chunkList)

        return changed

