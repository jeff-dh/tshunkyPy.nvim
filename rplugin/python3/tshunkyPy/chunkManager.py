import ast
import logging

from .chunk import Chunk, DummyInitialChunk


class ExprPrintWrapper(ast.NodeTransformer):
    """Wraps all Expr-Statements in a call to print()"""
    def visit_Expr(self, node):
        new = ast.Expr(
                value = ast.Call(
                    func = ast.Name(id='printExpr', ctx=ast.Load()),
                    args = [node.value], keywords = [])
                )
        ast.copy_location(new, node)
        ast.fix_missing_locations(new)
        return new


class ChunkManager(object):
    def __init__(self, outputManager):
        self.chunkList = []
        self.chunks = {}
        self.outputManager = outputManager

        self.isRunable = False

    def _parseSource(self, source):
        try:
            module_ast = ast.parse(source)
        except SyntaxError as e:
            self.isRunable = False
            self.outputManager.setSyntaxError(e)
            return None

        self.outputManager.setSyntaxError(None)
        self.isRunable = True

        # wrap every expression statement into a print call
        return ExprPrintWrapper().visit(module_ast)


    def update(self, source, filename='<string>'):
        changed = False

        module_ast = self._parseSource(source)
        if not module_ast:
            return False

        #reset chunkList
        self.chunkList = []
        prevChunk = DummyInitialChunk({})
        prevChash = 0

        for n in module_ast.body:
            # calculate chunk hash
            sourceChunk = ast.get_source_segment(source, n)
            chash = f'{prevChash}{sourceChunk}'.__hash__()

            self.chunkList.append(chash)

            # update chunk or create new one
            if chash in self.chunks:
                # chunk (and it predecessors) did not change
                # there might have been a whitespace change
                chunk = self.chunks[chash]
                chunk.update(n)
            else:
                # chunk or a predecessor changed
                # create new chunk
                chunk = Chunk(n, sourceChunk, filename, prevChunk,
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

