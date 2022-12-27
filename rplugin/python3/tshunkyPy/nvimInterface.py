from .chunkManager import ChunkManager
from .outputManager import OutputManager
from .utils.nvimUtils import createBuffer, modifiable, NvimLock
from .config import config, TshunkyPyKeymap

from pynvim import Nvim
from pynvim.api.common import NvimError
from textwrap import wrap
from contextlib import suppress

class NvimInterface:

    def __init__(self, nvim: Nvim):
        self.nvim = nvim

        self.buf = self.nvim.current.buffer
        self.ID = str(self.buf.handle)

        self.outputManager = OutputManager(self.nvim)
        self.keymapManager = TshunkyPyKeymap(self.nvim)
        self.chunkManager = ChunkManager(self.outputManager)

        self.liveMode = False
        self.popupBuffer = None
        self.nlock = NvimLock(nvim)

        self.initAutoCmds()

        self.nvim.api.command(f'lua vim.diagnostic.disable({self.buf.handle})')


    def initAutoCmds(self):
        create_autocmd = self.nvim.api.create_autocmd
        create_augroup = self.nvim.api.create_augroup

        def autocmd(events, cmd):
            create_autocmd(events, {'group': 'tshunkyPyAutoCmds' + self.ID,
                                    'buffer': self.buf.handle, 'command': cmd})

        create_augroup("tshunkyPyAutoCmds" + self.ID, {'clear': True})

        autocmd(['CursorMoved', 'CursorMovedI'],
                     f'call TshunkyPyCursorMovedCallback({self.ID})')
        autocmd(['CursorHold', 'CursorHoldI'],
                     f'call TshunkyPyCursorHoldCallback({self.ID})')
        autocmd(config.liveTriggerEvents,
                     f'call TshunkyPyLiveCallback({self.ID})')


    def quit(self):
        self.outputManager.echo('tshunkyPy quit....')

        # delete autocmds
        self.nvim.api.clear_autocmds({'group': 'tshunkyPyAutoCmds' + self.ID})

        # enable diagnostics
        self.nvim.api.command(f'lua vim.diagnostic.enable({self.buf.handle})')

        # cleanup managers
        self.keymapManager.restore()
        self.outputManager.quit()

        # delete buffer
        if self.popupBuffer:
            self.nvim.api.command(f'bw {self.popupBuffer.handle}')
            self.popupBuffer = None

    def cursorMoved(self):
        if not self.popupBuffer:
            return

        winid = self.nvim.funcs.bufwinid(self.popupBuffer.handle)

        if winid != -1:
            # hmmm can't figure out why this throws an exception when the
            # popup was focused and the cursor leaves the popup
            # it throws an winid invalid exception....?!?!
            # anyway it closes the window
            with suppress(NvimError):
                self.nvim.api.win_close(winid, True)

    def cursorHold(self):
        # get vtexts and stdout of "selected" chunk and prepare it
        lineno, col = self.nvim.funcs.getpos('.')[1:-1]
        chunk = self.chunkManager._getChunkByLine(lineno)
        if not chunk:
            return

        lines = [l for chunk in self.chunkManager._getOrderedChunks()
                   if lineno in chunk.vtexts.keys()
                   for l in '\n'.join(chunk.vtexts[lineno]).split('\n')]

        if chunk.stdout:
            lines.extend(chunk.stdout.rstrip('\n').split('\n'))

        lines = [wline for line in lines
                       for wline in wrap(line, config.popupWidth-1)]

        if not len(lines) > 1:
            return

        # create buffer
        if not self.popupBuffer or not self.popupBuffer.valid:
            self.popupBuffer = createBuffer(self.nvim, False, buftype='nofile')

        # set text
        with modifiable(self.popupBuffer):
            self.popupBuffer[:] = lines

        #window opts
        opts = {'relative': 'cursor',
                'width': config.popupWidth,
                'height': len(lines),
                'col': len(self.nvim.current.line) + 5 - col,
                'style': 'minimal',
                'row': 1,
        }

        #create / update window
        winid = self.nvim.funcs.bufwinid(self.popupBuffer.handle)
        if winid == -1:
            self.nvim.api.open_win(self.popupBuffer, False, opts)
        else:
            with suppress(NvimError):
                self.nvim.api.win_set_config(winid, opts)

    def liveCallback(self):
        if self.liveMode and config.liveCommand:
            self.nvim.api.command(config.liveCommand)
        elif not self.liveMode and config.semiLiveCommand:
            self.nvim.api.command(config.semiLiveCommand)

    def live(self):
        self.liveMode =  not self.liveMode
        if self.liveMode:
            self.outputManager.echo('tshunkyPy live mode is enabled')
            self.liveCallback()
        else:
            self.outputManager.echo('tshunkyPy live mode is disabled')

    def _update_raw(self):
        source = '\n'.join(self.buf[:])
        return self.chunkManager.update(source, self.buf.name)

    def update(self):
        with self.nlock:
            self._update_raw()

    def runAll(self):
        with self.nlock:
            self._update_raw()
            self.chunkManager.executeAllChunks()

    def runAllInvalid(self):
        with self.nlock:
            self._update_raw()
            self.chunkManager.executeAllInvalidChunks()

    def runFirstInvalid(self):
        with self.nlock:
            self._update_raw()
            self.chunkManager.executeFirstInvalidChunk()

    def runRange(self, selectedRange):
        # keep visual selection
        if len(selectedRange) > 1:
            self.nvim.api.input('gv')
        with self.nlock:
            self._update_raw()
            self.chunkManager.executeRange(selectedRange)

    def showStdout(self):
        stdoutBuf = self.outputManager.stdoutBuffer
        assert stdoutBuf

        mainWinId = self.nvim.current.window.handle

        winid = self.nvim.funcs.bufwinid(stdoutBuf.handle)
        if winid == -1:
            mainWinWidth = self.nvim.current.window.width
            mainWinHeight = self.nvim.current.window.height
            if mainWinWidth > 80:
                self.nvim.command(f'vsp #{stdoutBuf.handle}')
                self.nvim.current.window.width = int(mainWinWidth / 3)
            else:
                self.nvim.command(f'sp #{stdoutBuf.handle}')
                self.nvim.current.window.height = int(mainWinHeight / 3)
            stdoutBuf.api.set_option('buflisted', False)
            self.nvim.funcs.win_gotoid(mainWinId)
        else:
            self.nvim.api.win_close(winid, True)
