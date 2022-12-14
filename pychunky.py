from chunkCache import ChunkCache


chunkCache = ChunkCache()


def smartExecute(source):
    chunkCache.update(source, '<none>')
    while True:
        chunk, chash, state = chunkCache.getFirstInvalidChunk()
        if not chunk:
            break

        try:
            exec(chunk, state)
        except Exception:
            import traceback
            print(traceback.format_exc())
            break
        else:
            chunkCache.updateState(chash, state)


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
