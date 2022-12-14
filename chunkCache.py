import ast


class ChunkCache(object):
    def __init__(self):
        self.chunkList = []
        self.invalidChunks = []

        self.objCache = {}
        self.stateCache = {}
        self.chunk2obj = {}

    def getFirstInvalidChunk(self):
        if not self.invalidChunks:
            return None, None, None

        chash = self.invalidChunks[0]
        objHash = self.chunk2obj[chash]
        chunkId = self.chunkList.index(chash)

        preState = {}
        if chunkId > 0:
            prevHash = self.chunkList[chunkId-1]
            preState = self.stateCache[prevHash]

        return self.objCache[objHash], chash, dict(preState)

    def _cleanUpCaches(self):
        chunk2objSet = set(self.chunk2obj.keys())
        listSet = set(self.chunkList)
        for chash in chunk2objSet - listSet:
            print(f'deleting {chash}')
            assert chash not in self.chunkList

            objHash = self.chunk2obj[chash]
            del self.chunk2obj[chash]

            # if the previous execution failed (exception) there might be no
            # state....
            if chash in self.stateCache.keys():
                del self.stateCache[chash]

            # there might be multiple chash pointing to the same objHash...
            # same code produces same objHash, actually same object!
            objDead = objHash not in self.chunk2obj.values()
            if objDead:
                del self.objCache[objHash]

    def update(self, source, filename='<string>'):
        module_ast = ast.parse(source)

        self.chunkList = []
        self.invalidChunks = []

        prevHash = 0
        for n in module_ast.body:

            # compile code object
            objHash, updated = self._updateObjCache(n, filename)

            # calculate chunk hash
            chash = (objHash + prevHash).__hash__()
            self.chunkList.append(chash)

            # check whether chunk hash is "new" and add it
            if chash not in self.chunk2obj.keys():
                updated = True
                self.chunk2obj[chash] = objHash
            else:
                assert not updated

            if updated:
                print(f'invalidating {chash}')
                self.invalidChunks.append(chash)
            elif self.invalidChunks:
                # if one chunks is invalid all following chunks are invalid
                self.invalidChunks.append(chash)

            prevHash = chash

        self._cleanUpCaches()

    def _updateObjCache(self, node, filename):
        objhash = ast.unparse(node).__hash__()
        if objhash in self.objCache.keys():
            return objhash, False

        wrapperModule = ast.Module(body=[node], type_ignores=[])
        self.objCache[objhash] = compile(wrapperModule, filename, 'exec')

        return objhash, True

    def updateState(self, chash, state):
        self.stateCache[chash] = state
        self.invalidChunks.remove(chash)
