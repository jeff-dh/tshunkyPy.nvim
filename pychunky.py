import ast


def foo():
    print(1)


chunkCache = {}


def cleanupChunkCache(chunkList):
    cacheSet = set(list(chunkCache.keys()))
    for k in set(chunkList):
        cacheSet.remove(k)
    for k in cacheSet:
        assert k not in chunkList
        print(f'deleting {k}')
        del chunkCache[k]
        # chunkCache.pop(k)


def buildChunks(source, filename):
    # parse source and build ast
    module_ast = ast.parse(source)

    chunks = []
    changedChunks = []
    for n in module_ast.body:
        chunkHash = ast.unparse(n).__hash__()
        chunks.append(chunkHash)
        sourceHint = ast.get_source_segment(source, n).split('\n')[0]
        # print(f'{sourceHint:40.40} -> {chunkHash}')

        wrapperModule = ast.Module(body=[n], type_ignores=[])
        if chunkHash not in chunkCache.keys():
            changedChunks.append(chunkHash)
            print(f'updating: {sourceHint:30.30} ({chunkHash})')
            chunkCache[chunkHash] = compile(wrapperModule, filename, 'exec')

    return chunks, changedChunks


def smartExecute(source):
    chunks, changedChunks = buildChunks(source, '<none>')

    cleanupChunkCache(chunks)

    if not changedChunks:
        return

    firstChangedChunkHash = changedChunks.pop(0)
    firstChangedChunkId = chunks.index(firstChangedChunkHash)
    try:
        for k in chunks[firstChangedChunkId:]:
            exec(chunkCache[k])
    except Exception:
        # import traceback
        print("Exception")
        # traceback.print_exc()


def test(filename):
    with open(filename, 'r') as w:
        source = w.read()
        smartExecute(source)


if __name__ != '__main__':
    test('test3.py')
else:
    while True:
        print("==================")
        test('test3.py')
        import time
        time.sleep(2)
