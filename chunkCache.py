import ast
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

    def update(self, sourceChunk, lineno, end_lineno):
        self.sourceChunk = sourceChunk
        self.lineno = lineno
        self.end_lineno = end_lineno

    def execute(self, initialNamespace):
        logging.debug('exec %s', self.getDebugId())

        self.postState = dict(self.prevChunk.postState) if self.prevChunk \
                                    else initialNamespace

        try:
            exec(self.codeObject, self.postState)
        except Exception:
            import traceback
            print(traceback.format_exc())
            return False

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
        self.invalidChunks = []

        self.objCache = {}
        self.chunks = {}

        self.initialNamespace = initialNamespace

    def update(self, source, filename='<string>'):
        module_ast = ast.parse(source)

        # wrap every expression statement into a print call
        module_ast = ExprPrintWrapper().visit(module_ast)
        ast.fix_missing_locations(module_ast)

        self.chunkList = []
        self.invalidChunks = []

        prevChunk = None
        for n in module_ast.body:
            # calculate (code) object hash
            sourceChunk = ast.get_source_segment(source, n)
            objHash = sourceChunk.__hash__()

            # calculate chunk hash
            prevHash = prevChunk.chash if prevChunk else 0
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

                #append to invalid chunks
                self.invalidChunks.append(chunk)

                logging.debug('changed %s', self.chunks[chash].getDebugId())

            prevChunk = chunk

        self._cleanUpCaches()

    def executeFirstInvalidChunk(self):
        if not self.invalidChunks:
            return False

        if self.invalidChunks[0].execute(self.initialNamespace):
            self.invalidChunks.pop(0)
            return True

        return False

    def executeChunkByLine(self, line):
        for chunk in self.chunks.values():
            if line in chunk.lineRange:
                return chunk.execute(self.initialNamespace)

        return False

    def executeChunksByRange(self, start, end):
        rangeSet = set(range(start, end+1))

        for chunk in self.chunks.values():
            if len(rangeSet.intersection(chunk.lineRange)):
                if not chunk.execute(self.initialNamespace):
                    return False

        return True

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

