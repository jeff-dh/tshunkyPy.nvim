from .nvimInterface import NvimInterface

import pynvim


@pynvim.plugin
class NvimPlugin:
    synced = False

    def __init__(self, nvim: pynvim.Nvim):
        self.nvimInterfaces = {}
        self.nvim = nvim

    def getInterface(self):
        bufId = self.nvim.current.buffer.handle
        if bufId not in self.nvimInterfaces.keys():
            self.nvimInterfaces[bufId] = NvimInterface(self.nvim)
        return self.nvimInterfaces[bufId]

    @pynvim.command('TshunkyPy', sync=synced)
    def init(self):
        self.getInterface()
        self.update()

    @pynvim.command('TshunkyPyQuit', sync=synced)
    def quit(self):
        bufId = self.nvim.current.buffer.handle
        self.getInterface().quit()
        del self.nvimInterfaces[bufId]

    @pynvim.command('TshunkyPyLive', sync=synced)
    def live(self):
        self.getInterface().live()

    @pynvim.command('TshunkyPyUpdate', sync=synced)
    def update(self):
        self.getInterface().update()

    @pynvim.command('TshunkyPyRunAll', sync=synced)
    def runAll(self):
        self.getInterface().runAll()

    @pynvim.command('TshunkyPyRunAllInvalid', sync=synced)
    def runAllInvalid(self):
        self.getInterface().runAllInvalid()

    @pynvim.command('TshunkyPyRunFirstInvalid', sync=synced)
    def runFirstInvalid(self):
        self.getInterface().runFirstInvalid()

    @pynvim.command('TshunkyPyShowStdout', sync=synced)
    def showStdout(self):
        self.getInterface().showStdout()

    @pynvim.function('TshunkyPyLiveCallback', sync=False)
    def liveCallback(self, _):
        self.getInterface().liveCallback()

    @pynvim.function('TshunkyPyCursorMovedCallback', sync=False)
    def cursorMoved(self, _):
        self.getInterface().cursorMoved()

    @pynvim.function('TshunkyPyCursorHoldCallback', sync=False)
    def cursorHold(self, _):
        self.getInterface().cursorHold()

