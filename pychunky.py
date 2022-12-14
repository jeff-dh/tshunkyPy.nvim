from .chunkCache import ChunkCache


chunkCache = ChunkCache()


def smartExecute(source):
    chunkCache.update(source, '<none>')

    while True:
        ret, success = chunkCache.executeFirstInvalidChunk()
        if not success:
            break

        if ret:
            print(ret)

def smartExecuteFile(filename):
    with open(filename, 'r') as w:
        source = w.read()
        smartExecute(source)


if __name__ != '__main__':
    smartExecuteFile('test3.py')
else:
    while True:
        print('---------------------------')
        smartExecuteFile('pychunky/test3.py')
        import time
        time.sleep(2)

