from .nvimInterface import NvimInterface
from .config import config
from .utils.nvimUtils import NvimLock

from pynvim import Nvim, plugin, command, function


@plugin
class NvimPlugin:
    synced = False

    def __init__(self, nvim: Nvim):
        self.nvimInterfaces = {}
        self.nvim = nvim

        self.lock = NvimLock(self.nvim)

        luaConfig = self.nvim.exec_lua('return require("tshunkyPy").getConfig()')
        if luaConfig:
            config.update(luaConfig)

    def getInterface(self):
        with self.lock:
            bufId = self.nvim.current.buffer.handle
            if bufId not in self.nvimInterfaces.keys():
                self.nvimInterfaces[bufId] = NvimInterface(self.nvim)
            return self.nvimInterfaces[bufId]

    @command('TshunkyPy', sync=synced)
    def init(self):
        self.getInterface()
        self.update()

    @command('TshunkyPyQuit', sync=synced)
    def quit(self):
        bufId = self.nvim.current.buffer.handle
        self.getInterface().quit()
        del self.nvimInterfaces[bufId]

    @command('TshunkyPyLive', sync=synced)
    def live(self):
        self.getInterface().live()

    @command('TshunkyPyUpdate', sync=synced)
    def update(self):
        self.getInterface().update()

    @command('TshunkyPyRunAll', sync=synced)
    def runAll(self):
        self.getInterface().runAll()

    @command('TshunkyPyRunAllInvalid', sync=synced)
    def runAllInvalid(self):
        self.getInterface().runAllInvalid()

    @command('TshunkyPyRunFirstInvalid', sync=synced)
    def runFirstInvalid(self):
        self.getInterface().runFirstInvalid()

    @command('TshunkyPyRunRange', range='', sync=synced)
    def runRange(self, srange):
        self.getInterface().runRange(range(srange[0], srange[1]+1))

    @command('TshunkyPyShowStdout', sync=synced)
    def showStdout(self):
        self.getInterface().showStdout()

    def getInterfaceFromArgs(self, args):
        assert len(args) == 1
        bufID = int(args[0])
        assert bufID
        assert bufID in self.nvimInterfaces.keys()
        return self.nvimInterfaces[bufID]

    @function('TshunkyPyLiveCallback', sync=False)
    def liveCallback(self, args):
        self.getInterfaceFromArgs(args).liveCallback()

    @function('TshunkyPyCursorMovedCallback', sync=False)
    def cursorMoved(self, args):
        self.getInterfaceFromArgs(args).cursorMoved()

    @function('TshunkyPyCursorHoldCallback', sync=False)
    def cursorHold(self, args):
        self.getInterfaceFromArgs(args).cursorHold()

