from .chunkManager import ChunkManager
from .outputManager import OutputManager

import pynvim
import textwrap
import threading


class NvimLock:
    def __init__(self, nvim):
        self.nvim = nvim
        self.lock = threading.Lock()

    def __enter__(self):
        while not self.lock.acquire(blocking=False):
            #noop as yield, couldn't find any better solution....
            self.nvim.api.command('')

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.lock.release()

class NvimInterface:

    def __init__(self, nvim: pynvim.Nvim):
        self.nvim = nvim

        buf = self.nvim.current.buffer
        self.ID = str(buf.handle)

        self.outputManager = OutputManager(self.nvim)
        self.chunkManager = ChunkManager(self.outputManager)
        self.liveMode = False

        self.popupBuffer = None
        self.nlock = NvimLock(nvim)

        self.setKeymaps()

        self.nvim.api.command(f'lua vim.diagnostic.disable({buf.handle})')

    def echo(self, x):
        if not isinstance(x, str):
            x = repr(x)
        x = x.replace('\"', '\'')
        self.nvim.out_write(x + '\n')

    def autocmd(self, events, cmd, group=None):
        if group == None:
            group = 'tshunkyPyAutoCmds' + self.ID
        buf = self.nvim.current.buffer
        self.nvim.api.create_autocmd(events, {'group': group,
                                              'buffer': buf.handle,
                                              'command': cmd})

    def setKeymaps(self):
        buf = self.nvim.current.buffer
        keymap = buf.api.set_keymap
        opts = { 'silent': True, 'noremap': True, 'nowait': True}

        keymap('n', '<M-u>', ':TshunkyPyUpdate<CR>', opts)
        keymap('n', '<M-a>', ':TshunkyPyRunAll<CR>', opts)
        keymap('n', '<M-i>', ':TshunkyPyRunAllInvalid<CR>', opts)
        keymap('n', '<M-f>', ':TshunkyPyRunFirstInvalid<CR>', opts)
        keymap('n', '<M-x>', ':TshunkyPyLive<CR>', opts)
        keymap('n', '<M-o>', ':TshunkyPyShowStdout<CR>', opts)

        keymap('i', '<M-u>', '<ESC>:TshunkyPyUpdate<CR>li', opts)
        keymap('i', '<M-a>', '<ESC>:TshunkyPyRunAll<CR>li', opts)
        keymap('i', '<M-i>', '<ESC>:TshunkyPyRunAllInvalid<CR>li', opts)
        keymap('i', '<M-f>', '<ESC>:TshunkyPyRunFirstInvalid<CR>li', opts)
        keymap('i', '<M-x>', '<ESC>:TshunkyPyLive<CR>li', opts)
        keymap('i', '<M-o>', '<ESC>:TshunkyPyShowStdout<CR>li', opts)

        create_augroup = self.nvim.api.create_augroup
        create_augroup("tshunkyPyAutoCmds" + self.ID, {'clear': True})
        create_augroup("tshunkyPyAutoLiveCmd" + self.ID, {'clear': True})
        create_augroup("tshunkyPyAutoCursorMovedCmd" + self.ID, {'clear': True})

        self.autocmd(['CursorHold', 'CursorHoldI'],
                     'call TshunkyPyCursorHoldCallback()')

        self.updateAutoCommands()

    def quit(self):
        buf = self.nvim.current.buffer
        clear_autocmds = self.nvim.api.clear_autocmds
        command = self.nvim.api.command

        clear_autocmds({'group': 'tshunkyPyAutoCursorMovedCmd' + self.ID})
        clear_autocmds({'group': 'tshunkyPyAutoCmds' + self.ID})
        clear_autocmds({'group': 'tshunkyPyAutoLiveCmd' + self.ID})

        command(f'lua vim.diagnostic.enable({buf.handle})')

        self.outputManager.quit()

        if self.popupBuffer:
            command(f'bw {self.popupBuffer.handle}')
            self.popupBuffer = None

    def cursorMoved(self):
        self.nvim.api.clear_autocmds(
                {'group': 'tshunkyPyAutoCursorMovedCmd' + self.ID})

        assert self.popupBuffer
        winid = self.nvim.funcs.bufwinid(self.popupBuffer.handle)

        if winid != -1:
            # hmmm can't figure out why this throws an exception when the
            # popup was focused and the cursor leaves the popup
            # it throws an winid invalid exception....?!?!
            # anyway it closes the window
            try:
                self.nvim.api.win_close(winid, True)
            except pynvim.api.common.NvimError: # type: ignore
                pass

    def cursorHold(self):
        popupWidth = 80

        # get stdout of "selected" chunk and prepare it
        lineno, col = self.nvim.funcs.getpos('.')[1:-1]
        chunk = self.chunkManager._getChunkByLine(lineno)
        if not chunk or not chunk.stdout:
            return

        lines = chunk.stdout.strip().split('\n')
        lines = [wline for line in lines
                       for wline in textwrap.wrap(line, popupWidth-1)]

        if not len(lines) > 1:
            return

        # create buffer
        if not self.popupBuffer or not self.popupBuffer.valid:
            self.popupBuffer = self.nvim.api.create_buf(False, True)
            self.popupBuffer.api.set_option('buftype', 'nofile')
            self.popupBuffer.api.set_option('buflisted', False)

        # set text
        self.popupBuffer.api.set_option('modifiable', True)
        self.popupBuffer[:] = lines
        self.popupBuffer.api.set_option('modifiable', False)

        #window opts
        opts = {'relative': 'cursor',
                'width': popupWidth,
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

            self.autocmd(['CursorHold', 'CursorHoldI'],
                         'TshunkyPyRunAllInvalid',
                         'tshunkyPyAutoLiveCmd' + self.ID)

            self.runAllInvalid()
        else:
            self.echo('tshunkyPy live mode is disabled')

            self.nvim.api.clear_autocmds(
                    {'group': 'tshunkyPyAutoLiveCmd' + self.ID})

            self.autocmd(['CursorHold', 'CursorHoldI'],
                         'TshunkyPyUpdate',
                         'tshunkyPyAutoLiveCmd' + self.ID)

    def live(self):
        self.liveMode =  not self.liveMode
        self.updateAutoCommands()

    def update(self):
        with self.nlock:
            buf = self.nvim.current.buffer
            source = '\n'.join(buf[:])

            return self.chunkManager.update(source, buf.name)

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
