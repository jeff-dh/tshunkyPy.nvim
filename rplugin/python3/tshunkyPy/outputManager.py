import pynvim
from .config import config


class ChunkOutputHandler:
    def  __init__(self, chash, buf, nvim: pynvim.Nvim):
        self.nvim = nvim
        self.buf = buf

        self.id = str(chash)

        self.vtext_ns = self.nvim.api.create_namespace(
                                    f'tshunkyPyVirtualText{self.id}')
        self.signIds = []

    def cleanup(self):

        for sid in self.signIds:
            self.nvim.funcs.sign_unplace('tshunkyPySigns', {'id': sid})

        if self.vtext_ns:
            self.buf.api.clear_namespace(self.vtext_ns, 0, -1)

        self.signIds = []

    def _placeSign(self, name, lineno):
        # a (nice(r)) wrapper around sign_place(...)
        sign_place = self.nvim.funcs.sign_place

        i = sign_place(0, 'tshunkyPySigns', name, self.buf.handle,
                        {'lnum': lineno, 'priority': 20})
        self.signIds.append(i)

    def update(self, valid, lineRange, vtexts):
        # delete old stuff
        self.cleanup()

        # place signs and set bg color for invalid chunks
        if not valid:
            self._placeSign('tshunkyPyInvalidSign', lineRange.start)
            for lineno in lineRange:
                self._placeSign('tshunkyPyInvalidLine', lineno)

        # display the virtal text messages from vtexts
        for lno, text in vtexts:
            vtext = ['>> ' + text.replace('\n', '\\n'), 'tshunkyPyVTextHl']
            mark = {'virt_text': [vtext], 'priority': config.vtextPriority}
            self.buf.api.set_extmark(self.vtext_ns, lno-1, 0, mark)

class OutputManager:

    def __init__(self, buf, nvim):
        self.nvim = nvim
        self.buf = buf
        self.chunkSignHandlers = {}

        command = self.nvim.api.command
        sign_define = self.nvim.funcs.sign_define

        command('highlight tshunkyPyInvalidSignHl ' +
                f'{config.invalidSignHighlight}')
        command('highlight tshunkyPyInvalidLineHl ' +
                f'{config.invalidLineHighlight}')


        sign_define('tshunkyPyInvalidSign',
                    {'text': config.invalidSign,
                     'texthl': 'tshunkyPyInvalidSignHl'})
        sign_define('tshunkyPyInvalidLine',
                    {'linehl': 'tshunkyPyInvalidLineHl'})

        command(f'highlight tshunkyPyVTextHl {config.vtextHighlight}')

        buf = self.nvim.current.buffer
        self.stdoutBuffer = self.nvim.api.create_buf(False, True)
        self.stdoutBuffer.api.set_option('buftype', 'nofile')
        self.stdoutBuffer.api.set_option('buflisted', False)
        self.stdoutBuffer.name = buf.name + '.tshunkyPy.stdout'

    def deleteHandler(self, chash):
        if not chash in self.chunkSignHandlers.keys():
            return

        self.chunkSignHandlers[chash].cleanup()
        del self.chunkSignHandlers[chash]

    def quit(self):
        for handler in self.chunkSignHandlers.values():
            handler.cleanup()

        self.chunkSignHandlers = {}
        assert self.stdoutBuffer
        self.nvim.command(f'bw {self.stdoutBuffer.handle}')
        self.stdoutBuffer = None

    def update(self, chunk):
        # create handler if neccessary
        if not chunk.chash in self.chunkSignHandlers.keys():
            self.chunkSignHandlers[chunk.chash] = \
                    ChunkOutputHandler(chunk.chash, self.buf, self.nvim)

        # call handler.update
        handler = self.chunkSignHandlers[chunk.chash]
        handler.update(chunk.valid, chunk.lineRange, chunk.vtexts)

        # collect stdout and set stdoutBuffer
        if chunk.valid or chunk.prevChunk.valid:
            stdoutList = []
            c = chunk
            while c:
                if c.stdout:
                    stdoutList.extend(c.stdout.split('\n'))
                    if c.stdout.endswith('\n'):
                        stdoutList.pop()
                c = c.prevChunk

            assert self.stdoutBuffer
            stdoutList.reverse()
            self.stdoutBuffer.api.set_option('modifiable', True)
            self.stdoutBuffer[:] = stdoutList
            self.stdoutBuffer.api.set_option('modifiable', False)

    def setSyntaxError(self, e):
        shash = 'SyntaxError'.__hash__()

        if not e:
            self.deleteHandler(shash)
            return

        if not shash in self.chunkSignHandlers.keys():
            self.chunkSignHandlers[shash] = \
                    ChunkOutputHandler(shash, self.buf, self.nvim)

        handler = self.chunkSignHandlers[shash]

        handler.update(False, range(e.lineno, e.lineno + 1),
                       [(e.lineno, repr(e))])
