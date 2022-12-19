from pathlib import Path

import logging

logFormat = '%(levelname)s (%(filename)s:%(lineno)s): %(message)s'
logging.basicConfig(format=logFormat, level=logging.DEBUG)

from ..chunkManager import ChunkManager

chunkManager = ChunkManager()

def executeFile(filename):
    with open(filename, 'r') as w:
        source = w.read()

        chunkManager.update(source, filename)
        chunkManager.executeAllInvalidChunks()

        for lineno, msg, _ in chunkManager.getOutput():
            print(f'{Path(filename).name}:{lineno} {msg}')



if __name__ == '__main__':
    while True:
        print('--------')
        file = Path(__file__).parent / 'testSource.py'
        executeFile(file.as_posix())
        import time
        time.sleep(2)

