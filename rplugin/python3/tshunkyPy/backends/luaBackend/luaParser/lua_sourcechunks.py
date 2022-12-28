from .lua_parser import parse

def _makeChunk(source, lastLineno, lastPos, pos):
    sourceChunk = source[lastPos: pos].rstrip()

    posRange = range(lastPos, lastPos + len(sourceChunk)+1)
    lineRange = range(lastLineno, lastLineno + sourceChunk.count('\n') + 1)
    return ((lineRange, posRange), sourceChunk)

def getSourceChunks(source, filename):

    chunkPositions = parse(source, filename)
    if not isinstance(chunkPositions, list):
        # Syntax Error
        return chunkPositions

    chunks = []
    print(chunkPositions)
    lastLineno, lastPos = chunkPositions[0]
    for lineno, pos in chunkPositions[1:]:
        chunks.append(_makeChunk(source, lastLineno, lastPos, pos-1))

        lastPos = pos
        lastLineno = lineno

    chunks.append(_makeChunk(source, lastLineno, lastPos, -1))

    return chunks

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print(f'usage: {sys.argv[0]} <lua_file>')
        sys.exit(-1)

    with open(sys.argv[1]) as f:
        source = f.read()

    chunks = getSourceChunks(source, sys.argv[1])
    for lineAndPosInfo, csource in chunks:
        print('--------------')
        print(csource)

