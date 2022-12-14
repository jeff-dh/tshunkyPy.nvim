from pathlib import Path

import logging

logFormat = '%(levelname)s (%(filename)s:%(lineno)s): %(message)s'
logging.basicConfig(format=logFormat, level=logging.DEBUG)

from ..chunkManager import ChunkManager


def myPrint(*args, **kwargs):
    if not args:
        return
    if args[0] is None:
        return

    print(*args, **kwargs)

chunkManager = ChunkManager({'print': myPrint})

def executeFile(filename):
    with open(filename, 'r') as w:
        source = w.read()

        chunkManager.update(source, filename)

        chunkManager.executeAllInvalidChunks()


if __name__ == '__main__':
    while True:
        print('---------------------------')
        file = Path(__file__).parent / 'testSource.py'
        executeFile(file.as_posix())
        import time
        time.sleep(2)

