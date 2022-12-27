from .utils.nvimUtils import modifiable, createBuffer
from .config import config

from pynvim import Nvim
from pprint import pformat


class ChunkOutputHandler:
    def  __init__(self, cid, buf, nvim: Nvim, vtextPos='eol'):
        self.nvim = nvim
        self.buf = buf
        self.vtextPos = vtextPos

        self.id = str(cid)

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

    def update(self, valid, lineRange, vtexts, stdout):
        # delete old stuff
        self.cleanup()

        # place signs and set bg color for invalid chunks
        if not valid:
            self._placeSign('tshunkyPyInvalidSign', lineRange.start)
            for lineno in lineRange:
                self._placeSign('tshunkyPyInvalidLine', lineno)

        # display the virtal text messages from vtexts
        for lno, textList in vtexts.items():
            for text in reversed(textList):
                s = text.replace('\n', '\\n')
                vtext = [f'{config.vtextPrompt} ' + s, 'tshunkyPyVTextHl']
                mark = {'virt_text': [vtext],
                        'priority': config.vtextPriority,
                        'virt_text_pos': self.vtextPos}
                self.buf.api.set_extmark(self.vtext_ns, lno-1, 0, mark)

        # display virtual text messages from stdout
        if stdout:
            s = stdout.rstrip('\n').replace('\n', '\\n')
            vtext = [f'{config.vtextPrompt} ' + s, 'tshunkyPyVTextStdoutHl']
            mark = {'virt_text': [vtext], 'priority': config.vtextPriority + 1}
            self.buf.api.set_extmark(self.vtext_ns, lineRange.stop-2, 0, mark)


class OutputManager:

    def __init__(self, nvim):
        self.nvim = nvim
        self.buf = self.nvim.current.buffer
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
        command(f'highlight tshunkyPyVTextStdoutHl {config.vtextStdoutHighlight}')

        self.stdoutBuffer = \
            createBuffer(self.nvim, False, buftype='nofile',
                         name = self.buf.name + '.tshunkyPy.stdout')

    def echo(self, x):
        if not isinstance(x, str):
            x = pformat(x)
        assert x
        x = x.replace('\"', '\'')
        self.nvim.out_write(x + '\n')

    def delete(self, chunk):
        cid = id(chunk)
        if not cid in self.chunkSignHandlers.keys():
            return

        self.chunkSignHandlers[cid].cleanup()
        del self.chunkSignHandlers[cid]

    def quit(self):
        for handler in self.chunkSignHandlers.values():
            handler.cleanup()

        self.chunkSignHandlers = {}
        assert self.stdoutBuffer
        self.nvim.command(f'bw {self.stdoutBuffer.handle}')
        self.stdoutBuffer = None

    def update(self, chunk):
        cid = id(chunk)
        # create handler if neccessary
        if not cid in self.chunkSignHandlers.keys():
            self.chunkSignHandlers[cid] = \
                    ChunkOutputHandler(cid, self.buf, self.nvim)

        # call handler.update
        handler = self.chunkSignHandlers[cid]
        handler.update(chunk.valid, chunk.lineRange, chunk.vtexts, chunk.stdout)

        # collect stdout and set stdoutBuffer
        if chunk.valid or chunk.prevChunk.valid:
            stdoutList = []
            c = chunk if chunk.valid else chunk.prevChunk
            while c:
                if c.stdout:
                    stdoutList.extend(c.stdout.split('\n'))
                    if c.stdout.endswith('\n'):
                        stdoutList.pop()
                c = c.prevChunk

            assert self.stdoutBuffer
            stdoutList.reverse()

            title = ['TshunkyPy.stdout:',
                     '-----------------']
            with modifiable(self.stdoutBuffer):
                self.stdoutBuffer[:] = title  + stdoutList

    def setSyntaxError(self, e):
        shash = 'SyntaxError'.__hash__()

        if not e:
            self.delete(shash)
            return

        if not shash in self.chunkSignHandlers.keys():
            self.chunkSignHandlers[shash] = \
                    ChunkOutputHandler(shash, self.buf, self.nvim, 'right_align')

        handler = self.chunkSignHandlers[shash]

        handler.update(False, range(e.lineno, e.lineno + 1),
                       {e.lineno: ['SyntaxError']}, '')
