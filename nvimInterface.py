from .chunkManager import ChunkManager
from .utils import wrapLines

import pynvim


class NvimInterface:

    def __init__(self, nvim: pynvim.Nvim):
        self.nvim = nvim

        buf = self.nvim.current.buffer
        self.ID = str(buf.handle)

        self.chunkManager = ChunkManager()
        self.liveMode = False

        self.popupBuffer = None
        self.popupWindow = None
        self.stdoutBuffer = None

        self.setKeymaps()
        self.initSignsAndVText()

        self.nvim.api.command(f'lua vim.diagnostic.disable({buf.handle})')

    def echo(self, x):
        if not isinstance(x, str):
            x = repr(x)
        x = x.replace('\"', '\'')
        self.nvim.api.command(f'echo "{x}"')


    def initSignsAndVText(self):
        self.nvim.api.command('highlight tshunkyPyInvalidhl guibg=red')
        self.nvim.api.command('highlight tshunkyPyInvalidhl2 guibg=#111111')

        invalidSign = {'text': '>>', 'texthl': 'tshunkyPyInvalidhl'}
        invalidSign2 = {'linehl': 'tshunkyPyInvalidhl2'}

        self.nvim.funcs.sign_define('tshunkyPyInvalidSign', invalidSign)
        self.nvim.funcs.sign_define('tshunkyPyInvalidSign2', invalidSign2)

        self.nvim.api.command('highlight tshunkyPyVTexthl gui=bold guifg=#22AADD')
        self.nvim.api.command('highlight tshunkyPyVErrorhl gui=bold guifg=#c84848')
        self.vtext_ns = self.nvim.api.create_namespace("tshunkyPyVirtualText")

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

        self.nvim.api.create_augroup("tshunkyPyAutoCmds" + self.ID, {'clear': True})
        self.nvim.api.create_augroup("tshunkyPyAutoLiveCmd" + self.ID, {'clear': True})
        self.nvim.api.create_augroup("tshunkyPyAutoCursorMovedCmd" + self.ID, {'clear': True})
        self.autocmd(['CursorHold', 'CursorHoldI'],
                     'call TshunkyPyCursorHoldCallback()')

        self.updateAutoCommands()

    def quit(self):
        buf = self.nvim.current.buffer

        buf.api.clear_namespace(self.vtext_ns, 0, -1)

        self.nvim.funcs.sign_unplace('tshunkyPyInvalidSignsGroup' + buf.name)

        self.nvim.api.clear_autocmds({'group': 'tshunkyPyAutoCursorMovedCmd' + self.ID})
        self.nvim.api.clear_autocmds({'group': 'tshunkyPyAutoCmds' + self.ID})
        self.nvim.api.clear_autocmds({'group': 'tshunkyPyAutoLiveCmd' + self.ID})

        self.nvim.api.command(f'lua vim.diagnostic.enable({buf.handle})')

        if self.stdoutBuffer:
            self.nvim.command(f'bw {self.stdoutBuffer.handle}')
            self.stdoutBuffer = None

        if self.popupBuffer:
            self.nvim.command(f'bw {self.popupBuffer.handle}')
            self.popupBuffer = None

    def cursorMoved(self):
        self.nvim.api.clear_autocmds({'group': 'tshunkyPyAutoCursorMovedCmd' + self.ID})
        assert self.popupWindow != None
        if self.popupWindow and self.popupWindow.valid:
            # hmmm can't figure out why this throws an exception when the
            # popup was focused and the cursor leaves the popup
            # it throws an winid invalid exception....?!?!
            # anyway it closes the window
            try:
                self.popupWindow.api.close(True)
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
        if not len(lines) > 1:
            return

        lines = wrapLines(lines, popupWidth-1)

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
        if not self.popupWindow or not self.popupWindow.valid:
            self.autocmd(['CursorMoved', 'CursorMovedI'],
                         'call TshunkyPyCursorMovedCallback()',
                         'tshunkyPyAutoCursorMovedCmd' + self.ID)
            self.popupWindow = self.nvim.api.open_win(self.popupBuffer, False, opts)
        else:
            self.popupWindow.api.set_config(opts)

    def updateAutoCommands(self):
        if self.liveMode:
            self.echo('Enabled tshunkyPy live mode')
            self.nvim.api.clear_autocmds({'group': 'tshunkyPyAutoLiveCmd' + self.ID})
            self.autocmd(['CursorHold', 'CursorHoldI'],
                         'call TshunkyPyLiveCallback()',
                         'tshunkyPyAutoLiveCmd' + self.ID)
            self.runAllInvalid()
        else:
            self.echo('Disabled tshunkyPy live mode')
            self.nvim.api.clear_autocmds({'group': 'tshunkyPyAutoLiveCmd' + self.ID})
            self.autocmd(['CursorHold', 'CursorHoldI'],
                         'TshunkyPyUpdate',
                         'tshunkyPyAutoLiveCmd' + self.ID)

    def live(self):
        self.liveMode =  not self.liveMode
        self.updateAutoCommands()

    def updateLive(self):
        if self.update():
            self.runAllInvalid()

    def update(self):
        buf = self.nvim.current.buffer
        source = '\n'.join(buf[:])

        # returns -1 on SyntaxError, False if nothing changed and
        # True if the source changed
        res = self.chunkManager.update(source, buf.name)
        if res:
            # either syntax error or updated source
            self._refresh()
            # updated source?
            return res == True

        # nothing changed
        return False

    def runAll(self):
        self.update()
        self.chunkManager.executeAllChunks()
        self._refresh()

    def runAllInvalid(self):
        self.update()
        while self.chunkManager.executeFirstInvalidChunk():
            self._refresh()
        self._refresh()

    def runFirstInvalid(self):
        self.update()
        self.chunkManager.executeFirstInvalidChunk()
        self._refresh()

    def _refreshInvalidRanges(self):
        buf = self.nvim.current.buffer

        # handle invaid ranges
        signGroup = 'tshunkyPyInvalidSignsGroup' + buf.name
        self.nvim.funcs.sign_unplace(signGroup)
        signList = []
        for r in self.chunkManager.getInvalidChunkRanges():
            signList.append({'buffer': buf.handle,
                                'group': signGroup,
                                'lnum': r.start,
                                'priority': 20,
                                'name': 'tshunkyPyInvalidSign'})
            for lineno in r:
                signList.append({'buffer': buf.handle,
                                    'group': signGroup,
                                    'lnum': lineno,
                                    'priority': 20,
                                    'name': 'tshunkyPyInvalidSign2'})

        try:
            self.nvim.funcs.sign_placelist(signList)
        except pynvim.api.common.NvimError: # type: ignore
            pass

    def _refreshVTexts(self):
        buf = self.nvim.current.buffer

        # handle chunk outputs
        buf.api.clear_namespace(self.vtext_ns, 0, -1)
        for lineno, text in self.chunkManager.getVTexts():
            vtext = ['>> ' + text.replace('\n', '\\n'), 'tshunkyPyVErrorhl']
            try:
                buf.api.set_extmark(self.vtext_ns, lineno-1, 0,
                                            {'virt_text': [vtext],
                                            'hl_mode': 'combine',
                                            'priority': 200})
            except pynvim.api.common.NvimError: # type: ignore
                pass

    def showStdout(self):
        if not self.stdoutBuffer:
            return

        mainWinId = self.nvim.current.window.handle

        winid = self.nvim.funcs.bufwinid(self.stdoutBuffer.handle)
        if winid == -1:
            mainWinWidth = self.nvim.current.window.width
            mainWinHeight = self.nvim.current.window.height
            if mainWinWidth > 80:
                self.nvim.command(f'vsp #{self.stdoutBuffer.handle}')
                self.nvim.current.window.width = int(mainWinWidth / 3)
            else:
                self.nvim.command(f'sp #{self.stdoutBuffer.handle}')
                self.nvim.current.window.height = int(mainWinHeight / 3)
            self.stdoutBuffer.api.set_option('buflisted', False)
            self.nvim.funcs.win_gotoid(mainWinId)
        else:
            self.nvim.api.win_close(winid, True)

    def _refreshStdout(self):
        buf = self.nvim.current.buffer

        if not self.stdoutBuffer or not self.stdoutBuffer.valid:
            self.stdoutBuffer = self.nvim.api.create_buf(False, True)
            self.stdoutBuffer.api.set_option('buftype', 'nofile')
            self.stdoutBuffer.api.set_option('buflisted', False)
            self.stdoutBuffer.name = buf.name + '.tshunkyPy.stdout'

        # set text
        lines = self.chunkManager.getStdout().split('\n')
        self.stdoutBuffer.api.set_option('modifiable', True)
        self.stdoutBuffer[:] = lines
        self.stdoutBuffer.api.set_option('modifiable', False)

    def _refresh(self):
        self._refreshInvalidRanges()
        self._refreshVTexts()
        self._refreshStdout()
