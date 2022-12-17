from .chunkManager import ChunkManager

import pynvim


gl_nvim = None
def debug(s):
    assert gl_nvim is not None
    s = repr(s).replace('\"', '\'')
    gl_nvim.api.command(f'echo "{s}"')


@pynvim.plugin
class NvimInterface:
    synced = False

    def __init__(self, nvim: pynvim.Nvim):
        self.nvim = nvim

        self.chunkManager = ChunkManager()
        self.liveMode = False

        self.popupBuffer = None
        self.popupWindow = None

        global gl_nvim
        gl_nvim = nvim

        self.setKeymaps()
        self.initSignsAndVText()

        buf = self.nvim.current.buffer
        self.nvim.api.command(f'lua vim.diagnostic.disable({buf.handle})')

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

    def autocmd(self, events, cmd, group='tshunkyPyAutoCmds'):
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
        keymap('v', '<M-r>', ':TshunkyPyRunRange<CR>', opts)
        keymap('n', '<M-l>', ':TshunkyPyRunLine<CR>', opts)
        keymap('n', '<M-x>', ':TshunkyPyLive<CR>', opts)

        self.nvim.api.create_augroup("tshunkyPyAutoCmds", {'clear': True})
        self.nvim.api.create_augroup("tshunkyPyAutoLiveCmd", {'clear': True})
        self.nvim.api.create_augroup("tshunkyPyAutoCursorMovedCmd", {'clear': True})
        self.autocmd(['CursorHold', 'CursorHoldI'], 'TshunkyPyCursorHold')

    @pynvim.command('TshunkyPy', sync=synced)
    def dummyInit(self):
        # to be able to init tshunkyPy and let it initialize it's key mappings
        # and auto commands
        pass

    @pynvim.command('TshunkyPyCursorMoved', sync=synced)
    def cursorMoved(self):
        self.nvim.api.clear_autocmds({'group': 'tshunkyPyAutoCursorMovedCmd'})
        if self.popupWindow and self.popupWindow.valid:
            self.popupWindow.api.close(True)

    @pynvim.command('TshunkyPyCursorHold', sync=synced)
    def cursorHold(self):
        lineno, col = self.nvim.funcs.getpos('.')[1:-1]
        chunk = self.chunkManager._getChunkByLine(lineno)

        if not chunk or not chunk.output:
            return

        lines = chunk.output.strip().split('\n')
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

        # make it cyan! Is there a better / faster way to paint the whole
        # buffer cyan?
        ns = self.nvim.api.create_namespace('tshunkyPyPopupHlns')
        for i in range(0, len(lines)):
            self.popupBuffer.api.add_highlight(ns, 'tshunkyPyVTexthl', i, 0, -1)

        #window opts
        opts = {'relative': 'cursor',
                'width': 50,
                'height': len(lines),
                'col': len(self.nvim.current.line) + 5 - col,
                'style': 'minimal',
                'row': 1,
        }

        #create / update window
        if not self.popupWindow or not self.popupWindow.valid:
            self.popupWindow = self.nvim.api.open_win(self.popupBuffer, False, opts)
            self.autocmd(['CursorMoved', 'CursorMovedI'], 'TshunkyPyCursorMoved',
                            'tshunkyPyAutoCursorMovedCmd')
        else:
            self.popupWindow.api.set_config(opts)

    @pynvim.command('TshunkyPyLive', sync=synced)
    def live(self):
        self.liveMode =  not self.liveMode
        if self.liveMode:
            self.autocmd(['CursorHold', 'CursorHoldI'],
                         'TshunkyPyUpdateAndRunInvalids',
                         'tshunkyPyAutoLiveCmd')
        else:
            self.nvim.api.clear_autocmds({'group': 'tshunkyPyAutoLiveCmd'})

    @pynvim.command('TshunkyPyUpdateAndRunInvalids', sync=False)
    def updateAndRunInvalids(self):
        if self.update():
            self.runAllInvalid()

    @pynvim.command('TshunkyPyUpdate', sync=synced)
    def update(self):
        buf = self.nvim.current.buffer
        source = '\n'.join(buf[:])

        res =  self.chunkManager.update(source, buf.name)
        if res != 0:
            self._refresh()
            return res == 1

        return False

    @pynvim.command('TshunkyPyRunAll', sync=synced)
    def runAll(self):
        self.chunkManager.executeAllChunks()
        self._refresh()

    @pynvim.command('TshunkyPyRunAllInvalid', sync=synced)
    def runAllInvalid(self):
        while self.chunkManager.executeFirstInvalidChunk():
            self._refresh()
        self._refresh()

    @pynvim.command('TshunkyPyRunFirstInvalid', sync=synced)
    def runFirstInvalid(self):
        self.chunkManager.executeFirstInvalidChunk()
        self._refresh()

    @pynvim.command('TshunkyPyRunLine', sync=synced)
    def runByLine(self):
        lineno = self.nvim.funcs.getpos('.')[1]
        self.chunkManager.executeChunkByLine(lineno)
        self._refresh()

    @pynvim.command('TshunkyPyRunRange', range='', sync=synced)
    def runByRange(self, selectedRange):
        self.chunkManager.executeChunksByRange(*selectedRange)
        self._refresh()

    def _refreshInvalidRanges(self):
        buf = self.nvim.current.buffer

        # handle invaid ranges
        signGroup = 'tshunky' + buf.name
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
        except pynvim.api.common.NvimError:
            pass

    def _refreshChunkOutputs(self):
        buf = self.nvim.current.buffer

        # handle chunk outputs
        buf.api.clear_namespace(self.vtext_ns, 0, -1)
        for pos, output, isError in self.chunkManager.getOutput():

            hl = 'tshunkyPyVTexthl' if not isError else 'tshunkyPyVErrorhl'
            vtext = ['>> ' + output.replace('\n', '\\n'), hl]

            try:
                buf.api.set_extmark(self.vtext_ns, pos-1, 0,
                                            {'virt_text': [vtext],
                                            'hl_mode': 'combine',
                                            'priority': 200 if not isError else 201})
            except pynvim.api.common.NvimError:
                pass


    def _refresh(self):
        self._refreshInvalidRanges()
        self._refreshChunkOutputs()
