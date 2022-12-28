from .luaBackend import parseLua, LuaChunk
from .pythonBackend import parsePy, PyChunk

parse = { 'python': parsePy, 'lua': parseLua}
Chunk = { 'python': PyChunk, 'lua': LuaChunk}
