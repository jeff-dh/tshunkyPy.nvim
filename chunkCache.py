import ast
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


class ExprPrintWrapper(ast.NodeTransformer):
    """Wraps all Expr-Statements in a call to print()"""
    def visit_Expr(self, node):
        new = ast.Expr(
                value = ast.Call(
                    func = ast.Name(id='print', ctx=ast.Load()),
                    args = [node.value], keywords = [])
                )
        ast.copy_location(new, node)
        ast.fix_missing_locations(new)
        return new


class ChunkManager(object):
    def __init__(self, initialNamespace):
        self.chunkList = []

        self.objCache = {}
        self.chunks = {}

        self.dummyInitialChunk = DummyInitialChunk(initialNamespace)

    def update(self, source, filename='<string>'):
        module_ast = ast.parse(source)

        # wrap every expression statement into a print call
        module_ast = ExprPrintWrapper().visit(module_ast)

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
                chunk = Chunk(chash, objHash, self.objCache[objHash], sourceChunk,
                            n.lineno, n.end_lineno, prevChunk)
                self.chunks[chash] = chunk

                logging.debug('changed %s', self.chunks[chash].getDebugId())

            prevChunk = chunk

        self._cleanUpCaches()

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
                if not chunk.execute():
                    return False
                return True
        return True

    def executeChunkByLine(self, line):
        for chunk in self._getOrderedChunks():
            if line in chunk.lineRange:
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

        return ranges

    def _getOrderedChunks(self):
        return [self.chunks[chash] for chash in self.chunkList]

    def _updateObjCache(self, node, objHash, filename):
        if objHash in self.objCache.keys():
            return

        wrapperModule = ast.Module(body=[node], type_ignores=[])
        self.objCache[objHash] = compile(wrapperModule, filename, 'exec')

    def _cleanUpCaches(self):
        chunksSet = set(self.chunks.keys())
        listSet = set(self.chunkList)
        for chash in chunksSet - listSet:
            logging.debug("deleted %s", self.chunks[chash].getDebugId())

            assert chash not in self.chunkList
            del self.chunks[chash]

        objSet = set(c.objHash for c in self.chunks.values())
        objCacheSet = set(self.objCache.keys())
        for objHash in objCacheSet - objSet:
            del self.objCache[objHash]

