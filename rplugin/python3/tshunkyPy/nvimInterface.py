from .chunkManager import ChunkManager
from .outputManager import OutputManager
from .utils.nvimUtils import createBuffer, modifiable, NvimLock
from .config import config

from pynvim import Nvim
from pynvim.api.common import NvimError
from textwrap import wrap

class NvimInterface:

    def __init__(self, nvim: Nvim):
        self.nvim = nvim

        self.buf = self.nvim.current.buffer
        self.ID = str(self.buf.handle)

        self.outputManager = OutputManager(self.buf, self.nvim)
        self.chunkManager = ChunkManager(self.outputManager)
        self.liveMode = False

        self.popupBuffer = None
        self.nlock = NvimLock(nvim)

        self.setKeymaps()

        self.nvim.api.command(f'lua vim.diagnostic.disable({self.buf.handle})')

    def echo(self, x):
        if not isinstance(x, str):
            x = repr(x)
        x = x.replace('\"', '\'')
        self.nvim.out_write(x + '\n')

    def autocmd(self, events, cmd, group=None):
        if group == None:
            group = 'tshunkyPyAutoCmds' + self.ID
        self.nvim.api.create_autocmd(events, {'group': group,
                                              'buffer': self.buf.handle,
                                              'command': cmd})

    def setKeymaps(self):
        keymap = self.buf.api.set_keymap
        opts = { 'silent': True, 'noremap': True, 'nowait': True}

        for cmd, keys in config.keymap.items():
            if not keys:
                continue
            keymap('n', keys, f':{cmd}<CR>', opts)
            if config.enableInsertKeymaps:
                keymap('i', keys, f'<ESC>:{cmd}<CR><right>i', opts)

        create_augroup = self.nvim.api.create_augroup
        create_augroup("tshunkyPyAutoCmds" + self.ID, {'clear': True})
        create_augroup("tshunkyPyAutoLiveCmd" + self.ID, {'clear': True})
        create_augroup("tshunkyPyAutoCursorMovedCmd" + self.ID, {'clear': True})

        self.autocmd(['CursorHold', 'CursorHoldI'],
                     'call TshunkyPyCursorHoldCallback()')

        self.updateAutoCommands()

    def quit(self):
        clear_autocmds = self.nvim.api.clear_autocmds
        command = self.nvim.api.command

        clear_autocmds({'group': 'tshunkyPyAutoCursorMovedCmd' + self.ID})
        clear_autocmds({'group': 'tshunkyPyAutoCmds' + self.ID})
        clear_autocmds({'group': 'tshunkyPyAutoLiveCmd' + self.ID})

        command(f'lua vim.diagnostic.enable({self.buf.handle})')

        self.outputManager.quit()

        if self.popupBuffer:
            command(f'bw {self.popupBuffer.handle}')
            self.popupBuffer = None

        self.echo('tshunkyPy quit....')

    def cursorMoved(self):
        self.nvim.api.clear_autocmds(
                {'group': 'tshunkyPyAutoCursorMovedCmd' + self.ID})

        # assert self.popupBuffer
        # this might happen if the popup box is open
        # and the open buffer changes
        if not self.popupBuffer:
            return

        winid = self.nvim.funcs.bufwinid(self.popupBuffer.handle)

        if winid != -1:
            # hmmm can't figure out why this throws an exception when the
            # popup was focused and the cursor leaves the popup
            # it throws an winid invalid exception....?!?!
            # anyway it closes the window
            try:
                self.nvim.api.win_close(winid, True)
            except NvimError:
                pass

    def cursorHold(self):

        # get stdout of "selected" chunk and prepare it
        lineno, col = self.nvim.funcs.getpos('.')[1:-1]
        chunk = self.chunkManager._getChunkByLine(lineno)
        if not chunk or not chunk.stdout:
            return

        lines = chunk.stdout.strip().split('\n')
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
            self.autocmd(['CursorMoved', 'CursorMovedI'],
                         'call TshunkyPyCursorMovedCallback()',
                         'tshunkyPyAutoCursorMovedCmd' + self.ID)
            self.nvim.api.open_win(self.popupBuffer, False, opts)
        else:
            self.nvim.api.win_set_config(winid, opts)

    def updateAutoCommands(self):
        if self.liveMode:
            self.echo('tshunkyPy live mode is enabled')

            self.nvim.api.clear_autocmds(
                    {'group': 'tshunkyPyAutoLiveCmd' + self.ID})

            self.autocmd(config.liveTriggerEvents,
                         config.liveCommand,
                         'tshunkyPyAutoLiveCmd' + self.ID)

            self.runAllInvalid()
        else:
            self.echo('tshunkyPy live mode is disabled')

            self.nvim.api.clear_autocmds(
                    {'group': 'tshunkyPyAutoLiveCmd' + self.ID})

            if config.semiLiveCommand:
                self.autocmd(config.liveTriggerEvents,
                             config.semiLiveCommand,
                            'tshunkyPyAutoLiveCmd' + self.ID)

    def live(self):
        self.liveMode =  not self.liveMode
        self.updateAutoCommands()

    def update(self):
        with self.nlock:
            source = '\n'.join(self.buf[:])

            return self.chunkManager.update(source, self.buf.name)

    def runAll(self):
        self.update()
        with self.nlock:
            self.chunkManager.executeAllChunks()

    def runAllInvalid(self):
        self.update()
        with self.nlock:
            self.chunkManager.executeAllInvalidChunks()

    def runFirstInvalid(self):
        self.update()
        with self.nlock:
            self.chunkManager.executeFirstInvalidChunk()

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
