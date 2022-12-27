from pathlib import Path

import time
import logging

logFormat = '%(levelname)s (%(filename)s:%(lineno)s): %(message)s'
logging.basicConfig(format=logFormat, level=logging.DEBUG)

from ..chunkManager import ChunkManager

class OutputManager:
    def update(self, chunk):
        if not chunk.vtexts:
            return

        ts = [f'{file.name}:{lno} {t}' for lno, t in chunk.vtexts]
        print('\n'.join(ts))

    def delete(self, chunk):
        pass

    def setSyntaxError(self, e):
        if e:
            print(repr(e))


if __name__ == '__main__':
    file = Path(__file__).parent / 'testSource.py'
    chunkManager = ChunkManager(OutputManager())

    while True:
        print('--------')
        with open(file.as_posix(), 'r') as w:
            source = w.read()

            chunkManager.update(source, file.as_posix())
            chunkManager.executeAllInvalidChunks()
        time.sleep(2)

