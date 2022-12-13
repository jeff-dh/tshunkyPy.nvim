import ast


class ChunkCache(object):
    def __init__(self):
        self.cache = {}
        self.stateCache = {}

    def cleanupChunkCache(self, chunkList):
        cacheSet = set(list(self.cache.keys()))
        listSet = set(chunkList)
        for k in cacheSet - listSet:
            assert k not in chunkList
            print(f'deleting {k}')
            del self.cache[k]
            del self.stateCache[k]

    def update(self, node, filename):
        chunkHash = ast.unparse(node).__hash__()
        if chunkHash in self.cache.keys():
            return chunkHash, False

        wrapperModule = ast.Module(body=[node], type_ignores=[])
        self.cache[chunkHash] = compile(wrapperModule, filename, 'exec')

        return chunkHash, True

    def getChunk(self, chunkHash):
        assert chunkHash in self.cache
        return self.cache[chunkHash]

    def updateState(self, chunkHash, state):
        self.stateCache[chunkHash] = state

    def getState(self, chunkHash):
        assert chunkHash in self.stateCache
        return self.stateCache[chunkHash]


chunkCache = ChunkCache()


def buildChunks(source, filename='<string>'):
    module_ast = ast.parse(source)

    chunks = []
    changedChunks = []
    for n in module_ast.body:

        chunkHash, updated = chunkCache.update(n, filename)
        chunks.append(chunkHash)
        if updated:
            changedChunks.append(chunkHash)

    return chunks, changedChunks


def smartExecute(source):
    chunks, changedChunks = buildChunks(source, '<none>')

    chunkCache.cleanupChunkCache(chunks)

    if not changedChunks:
        return

    firstChangedChunkHash = changedChunks.pop(0)
    firstChangedChunkId = chunks.index(firstChangedChunkHash)

    if firstChangedChunkId == 0:
        executionState = {}
    else:
        previousChunkHash = chunks[firstChangedChunkId-1]
        executionState = chunkCache.getState(previousChunkHash)
    try:
        for chunkHash in chunks[firstChangedChunkId:]:
            exec(chunkCache.getChunk(chunkHash), executionState)
            chunkCache.updateState(chunkHash, executionState)
    except Exception:
        import traceback
        print(traceback.format_exc())


def smartExecuteFile(filename):
    with open(filename, 'r') as w:
        source = w.read()
        smartExecute(source)


if __name__ != '__main__':
    smartExecuteFile('test3.py')
else:
    while True:
        print('---------------------------')
        smartExecuteFile('test3.py')
        import time
        time.sleep(2)

1
