import logging

from .chunk import DummyInitialChunk
from . import backends


class ChunkManager(object):
    def __init__(self, outputManager):
        self.chunkList = []
        self.chunks = {}
        self.outputManager = outputManager

        self.isRunable = False

    def update(self, source, filetype, filename='<string>'):
        changed = False

        astChunks = backends.parse[filetype](source, filename)

        if isinstance(astChunks, SyntaxError):
            self.isRunable = False
            self.outputManager.setSyntaxError(astChunks)
            return False

        self.isRunable = True
        self.outputManager.setSyntaxError(None)

        #reset chunkList
        self.chunkList = []
        prevChunk = DummyInitialChunk({})
        prevChash = 0

        FTChunk = backends.Chunk[filetype]
        for astNode, sourceChunk in astChunks:
            self.outputManager.echo(astNode)
            # calculate chunk hash
            chash = f'{prevChash}{sourceChunk}'.__hash__()

            self.chunkList.append(chash)

            # update chunk or create new one
            if chash in self.chunks:
                # chunk (and it predecessors) did not change
                # there might have been a whitespace change
                chunk = self.chunks[chash]
                chunk.update(astNode)
            else:
                # chunk or a predecessor changed
                # create new chunk
                chunk = FTChunk(astNode, sourceChunk, filename, prevChunk,
                                self.outputManager)
                self.chunks[chash] = chunk
                changed = True

                logging.debug('changed %s', self.chunks[chash].getDebugId())

            prevChunk = chunk
            prevChash = chash

        return self._cleanUpCache() or changed

    def executeAllChunks(self):
        if not self.isRunable:
            return False
        orderedChunks = self._getOrderedChunks()
        for chunk in orderedChunks:
            if chunk.valid:
                chunk.reset()

        for chunk in self._getOrderedChunks():
            if not chunk.execute():
                return False

        return True

    def executeAllInvalidChunks(self):
        if not self.isRunable:
            return False
        for chunk in self._getOrderedChunks():
            if not chunk.valid:
                if not chunk.execute():
                    return False
        return True

    def executeFirstInvalidChunk(self):
        if not self.isRunable:
            return False
        for chunk in self._getOrderedChunks():
            if not chunk.valid:
                return chunk.execute()

        return False

    def executeRange(self, selectedRange):
        if not self.isRunable:
            return False

        # find first chunk that overlapps with range and set all following
        # chukns invalid
        first = None
        last = None
        orderedChunks = self._getOrderedChunks()
        for chunk in orderedChunks:
            if not first and selectedRange.start < chunk.lineRange.stop:
                first = chunk

            if first and chunk.valid:
                chunk.reset()
            last = chunk

        # this happens when the last line in a buffer is empty and execRange
        # contains only the last empty line
        if not first:
            assert last
            if not last.valid:
                first = last
            else:
                return False

        while not first.prevChunk.valid:
            first = first.prevChunk

        # run all chunks until the first chunk after selectedRange
        idx = orderedChunks.index(first)
        for chunk in orderedChunks[idx:]:
            if chunk.lineRange.start > selectedRange.stop-1:
                break
            if not chunk.execute():
                return False

        return True

    def _getOrderedChunks(self):
        return [self.chunks[chash] for chash in self.chunkList]

    def _getChunkByLine(self, line):
        for chunk in self.chunks.values():
            if line in chunk.lineRange:
                return chunk
        return None

    def _cleanUpCache(self):
        changed = False
        chunksSet = set(self.chunks.keys())
        listSet = set(self.chunkList)
        for chash in chunksSet - listSet:
            logging.debug("deleted %s", self.chunks[chash].getDebugId())
            changed = True

            assert chash not in self.chunkList

            self.chunks[chash].cleanup()
            del self.chunks[chash]

        assert len(self.chunks) == len(self.chunkList)

        return changed

