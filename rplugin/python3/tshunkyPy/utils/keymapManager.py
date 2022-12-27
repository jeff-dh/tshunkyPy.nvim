from pynvim import Nvim

class KeymapManager:
    def __init__(self, nvim: Nvim):
        self.nvim = nvim
        self.buf = self.nvim.current.buffer

        self.stored = {}
        self.toRestore = {}

        self.store()

    def store(self):
        def key(km):
            return (km['mode'], km['lhs'])

        def value(km):
            opts = {'noremap': km['noremap'] == 1,
                    'silent': km['silent'] == 1,
                    'nowait': km['nowait']==1}
            if not 'rhs' in km.keys():
                return (None, opts)
            return (km['rhs'], opts)

        self.stored = \
            {key(km) : value(km) for mode in 'inv'
                                 for km in self.buf.api.get_keymap(mode)}

    def restore(self):
        for k, v in self.toRestore.items():
            mode, lhs = k
            if v != None:
                rhs, opts = v
                self.buf.api.set_keymap(mode, lhs, rhs, opts)
            else:
                self.buf.api.del_keymap(mode, lhs)

        self.toRestore.clear()

    def keymap(self, mode, lhs, rhs, opts=None):
        if not opts:
            opts = { 'silent': True, 'noremap': True, 'nowait': True}

        if not (mode, lhs) in self.stored.keys():
            self.toRestore[(mode, lhs)] = None
        else:
            rhs, sopts = self.stored[(mode, lhs)]
            if rhs == None:
                self.nvim.err_write( \
                        f'TshunkPy::KeymapManager: Can\'t map \'{lhs}\', because the ' + \
                        f'previous map can\'t be (re)stored afterwards\n')
                return
            self.toRestore[(mode, lhs)] = (rhs, sopts)

        self.buf.api.set_keymap(mode, lhs, rhs, opts)

