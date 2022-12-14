import ast
import logging


class Chunk(object):
    def __init__(self, chash, objHash, codeObjectTuple, sourceChunk, lineno,
                 end_lineno, prevChunk):

        self.chash = chash
        self.codeObjectTuple = codeObjectTuple
        self.objHash = objHash
        self.sourceChunk = sourceChunk
        self.lineno = lineno
        self.end_lineno = end_lineno
        self.prevChunk = prevChunk
        self.postState = None

    def update(self, sourceChunk, lineno, end_lineno):
        self.sourceChunk = sourceChunk
        self.lineno = lineno
        self.end_lineno = end_lineno

    def getDebugId(self):
        return f'{self.lineno}: {self.sourceChunk.splitlines()[0]}'


class ChunkCache(object):
    def __init__(self):
        self.chunkList = []
        self.invalidChunks = []

        self.objCache = {}
        self.chunks = {}

    def executeChunk(self, chunk):
        logging.debug('exec %s', chunk.getDebugId())
        assert chunk in self.chunks.values()

        chunk.postState = dict(chunk.prevChunk.postState) if chunk.prevChunk \
                                                          else {}

        try:
            obj, isExpression = chunk.codeObjectTuple
            if isExpression:
                return eval(obj, chunk.postState), True
            else:
                return exec(obj, chunk.postState), True
        except Exception:
            import traceback
            print(traceback.format_exc())
            return None, False

    def executeFirstInvalidChunk(self):
        if not self.invalidChunks:
            return None, False

        ret, success =  self.executeChunk(self.invalidChunks[0])

        if success:
            self.invalidChunks.pop(0)

        return ret, success

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

    def update(self, source, filename='<string>'):
        module_ast = ast.parse(source)

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

    def _updateObjCache(self, node, objHash, filename):
        if objHash in self.objCache.keys():
            return

        # wrapperModule = ast.Module(body=[node], type_ignores=[])
        # self.objCache[objHash] = compile(wrapperModule, filename, 'exec')
        if issubclass(type(node), ast.Expr):
            expressionWrapper = ast.Expression(node.value)
            self.objCache[objHash] = (compile(expressionWrapper, filename, 'eval'), True)
        else:
            wrapperModule = ast.Module(body=[node], type_ignores=[])
            self.objCache[objHash] = (compile(wrapperModule, filename, 'exec'), False)

