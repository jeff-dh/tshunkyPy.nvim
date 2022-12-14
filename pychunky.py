from .chunkCache import ChunkManager


def myPrint(*args, **kwargs):
    if not args:
        return
    if args[0] is None:
        return

    print(*args, **kwargs)

chunkManager = ChunkManager({'print': myPrint})


def smartExecute(source):
    chunkManager.update(source, '<none>')

    while chunkManager.executeFirstInvalidChunk():
        pass

    chunkManager.executeChunksByRange(27, 29)

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

