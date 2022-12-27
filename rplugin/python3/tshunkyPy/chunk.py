from .config import config

import sys
import ast
import logging
import dill
import types
import inspect
import traceback
import pprint
import copy

class GlobalsWrapper(dict):
    def __init__(self):
        super().__init__()
        self.data = None

    def setData(self, data):
        self.data = data

    def __getitem__(self, key):
        assert self.data
        return self.data.__getitem__(key)

    def __setitem__(self, key, value):
        assert self.data
        return self.data.__setitem__(key, value)

class Chunk(object):
    def __init__(self, node, sourceChunk, filename, prevChunk,
                 outputManager=None):

        self.sourceChunk = sourceChunk
        self.prevChunk = prevChunk
        self.outputManager = outputManager
        self.filename = filename
        self.node = node
        self.codeObject = None

        # all chunks -- of the same "execution chain" / ChunkManager -- share
        # the same globalState. Only for the DummyInitialChunk
        # (-> prevChunk is None) a new StateWrapper is created -- and shared
        # with all other chunks
        self.globalState = prevChunk.globalState if prevChunk \
                                                 else GlobalsWrapper()
        self.namespace = None

        # defines valid, stdout and vtexts
        self.reset()

    def reset(self):
        self._valid, self.stdout, self.vtexts = False, None, {}
        if self.outputManager:
            self.outputManager.update(self)

    @property
    def valid(self):
        return self._valid

    @property
    def lineRange(self):
        assert self.node
        return range(self.node.lineno, self.node.end_lineno + 1)

    def update(self, node):
        self.node = node

    def cleanup(self):
        assert self.outputManager
        self.outputManager.delete(self)

    def execute(self):
        logging.debug('exec %s', self.getDebugId())

        assert self.prevChunk
        assert self.prevChunk._valid

        # compile code if it's the first time we execute this chunk'
        if not self.codeObject or not config.reuseCodeObjects:
            wrapperModule = ast.Module(body=[self.node], type_ignores=[])
            self.codeObject = compile(wrapperModule, self.filename, 'exec')

        # store the sys.modules before we execute this chunk
        beforeModules = set([m for m in sys.modules.keys()])

        # derive namespace from prevChunk, based on a dill copy
        self.namespace = {}

        # copy functions and classes by reference! Otherwise their __globals__
        # field gets invalid
        for k, v in self.prevChunk.namespace.items():
            if isinstance(v, types.FunctionType) or isinstance(v, type):
                self.namespace[k] = v
            elif isinstance(v, types.ModuleType):
                self.namespace[k] = dill.copy(v)
            else:
                self.namespace[k] = copy.deepcopy(v)

        # inject locally wrapped print and printExpr functions
        printOutputs = {}
        def printExprWrapper(x):
            if x == None:
                return
            caller = inspect.getframeinfo(inspect.stack()[1][0])
            if not isinstance(x, str):
                x = pprint.pformat(x)
            printOutputs[caller.lineno] = printOutputs.get(caller.lineno, [])
            printOutputs[caller.lineno].append(x)

        self.namespace['printExpr'] = printExprWrapper

        # set our local namespace as "global namespace". This needs to be
        # wrapped, because all function objects contain a reference to the
        # global namespace (at chunk execution time! -> func.__globals__).
        # But since we want it to run on this chunks globals, we need a
        # wrapper to exchange the global namespace under the hood
        self.globalState.setData(self.namespace)

        # and execute the chunk and capture stdout
        with dill.temp.capture() as stdoutBuffer:
            error = None
            try:
                exec(self.codeObject, self.globalState)
            except Exception:
                _, _, tb = sys.exc_info()
                error = (traceback.extract_tb(tb)[-1][1],
                         traceback.format_exc())

        self.stdout = stdoutBuffer.getvalue()
        self.vtexts = dict(printOutputs)
        if error:
            self.stdout += '\n' + error[1]
            self.vtexts[error[0]] = self.vtexts.get(error[0], [])
            self.vtexts[error[0]].append(error[1])

        del self.namespace['printExpr']

        # unload modules that are not imported in the outside world
        # (outside of the exec envinronment) this is necessary to
        # make import xxxx work properly without reusing previously
        # imported instances and their state
        # buuut this does only work for modules that are not imported
        # in the outside world (outside the exec environment).....
        # I did not found a solution to save and restore the state of sys
        # for example... :(
        afterModules = set([m for m in sys.modules.keys()])
        for m in (afterModules - beforeModules):
            del sys.modules[m]

        self._valid = error == None

        assert self.outputManager
        self.outputManager.update(self)

        return self._valid

    def getDebugId(self):
        return f'{self.lineRange.start}: {self.sourceChunk.splitlines()[0]}'

class DummyInitialChunk(Chunk):
    def __init__(self, initialNamespace):
        super().__init__(None, None, None, None)
        self.namespace = initialNamespace
        self._valid = True

