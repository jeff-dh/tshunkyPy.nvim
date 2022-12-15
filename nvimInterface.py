from .chunkManager import ChunkManager

import pynvim


gl_nvim = None
def debug(s):
    assert gl_nvim is not None
    gl_nvim.api.command(f'echo "{s}"')


@pynvim.plugin
class NvimInterface:
    def __init__(self, nvim: pynvim.Nvim):
        self.chunkManager = ChunkManager({'print': self.print})
        self.nvim = nvim

        global gl_nvim
        gl_nvim = nvim

        self.setKeymaps()
        self.initInvalidSigns()

    def initInvalidSigns(self):
        self.nvim.api.command('highlight tshunkyPyInvalidhl guibg=red')
        self.nvim.api.command('highlight tshunkyPyInvalidhl2 guibg=#111111')

        invalidSign = {'text': '>>', 'texthl': 'tshunkyPyInvalidhl'}
        invalidSign2 = {'linehl': 'tshunkyPyInvalidhl2'}

        self.nvim.funcs.sign_define('tshunkyPyInvalidSign', invalidSign)
        self.nvim.funcs.sign_define('tshunkyPyInvalidSign2', invalidSign2)

    def setKeymaps(self):
        def keymap(mode, key, cmd):
            buf = self.nvim.current.buffer
            options = { 'silent': True, 'noremap': True, 'nowait': True}
            self.nvim.api.buf_set_keymap(buf.handle, mode, key, cmd, options)

        def autocmd(events, cmd):
            buf = self.nvim.current.buffer
            self.nvim.api.create_autocmd(events,
                                         {'group': 'tshunkyPyAutoCmds',
                                          'buffer': buf.handle,
                                          'command': cmd})

        keymap('n', '<leader>pu', ':TshunkyPyUpdate<CR>')
        keymap('n', '<leader>pa', ':TshunkyPyRunAll<CR>')
        keymap('n', '<leader>pi', ':TshunkyPyRunAllInvalid<CR>')
        keymap('n', '<leader>pf', ':TshunkyPyRunFirstInvalid<CR>')
        keymap('v', '<leader>pr', ':TshunkyPyRunRange<CR>')
        keymap('n', '<leader>pl', ':TshunkyPyRunLine<CR>')

        self.nvim.api.create_augroup("tshunkyPyAutoCmds", {'clear': True})

        autocmd(['CursorHold', 'CursorHoldI'], 'TshunkyPyUpdate')

    def print(self, *args, **kwargs):
        if args[0] == None:
            return

        self.nvim.command(f'echo "{args[0]}"')

    @pynvim.command('TshunkyPyUpdate', sync=True)
    def update(self):
        buf = self.nvim.current.buffer
        source = '\n'.join(buf[:])
        self.chunkManager.update(source, buf.name)
        self.updateInvalids()

    @pynvim.command('TshunkyPyRunAll', sync=True)
    def runAll(self):
        self.chunkManager.executeAllChunks()
        self.updateInvalids()

    @pynvim.command('TshunkyPyRunAllInvalid', sync=True)
    def runAllInvalid(self):
        self.chunkManager.executeAllInvalidChunks()
        self.updateInvalids()

    @pynvim.command('TshunkyPyRunFirstInvalid', sync=True)
    def runFirstInvalid(self):
        self.chunkManager.executeFirstInvalidChunk()
        self.updateInvalids()

    @pynvim.command('TshunkyPyRunLine', sync=True)
    def runByLine(self):
        lineno = self.nvim.funcs.getpos('.')[1]
        self.chunkManager.executeChunkByLine(lineno)
        self.updateInvalids()

    @pynvim.command('TshunkyPyRunRange', range='', sync=True)
    def runByRange(self, selectedRange):
        self.chunkManager.executeChunksByRange(*selectedRange)
        self.updateInvalids()

    @pynvim.command('TshunkyPyUpdateInvalids')
    def updateInvalids(self):
        buf = self.nvim.current.buffer
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

        self.nvim.funcs.sign_placelist(signList)
