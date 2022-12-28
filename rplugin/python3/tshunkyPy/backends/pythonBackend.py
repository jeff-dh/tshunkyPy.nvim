from ..config import config
from ..chunk import Chunk, DummyInitialChunk

import ast
import sys
import dill
import types
import inspect
import traceback
import pprint
import copy

def parsePy(source, filename):
    class ExprPrintWrapper(ast.NodeTransformer):
        """Wraps all Expr-Statements in a call to print()"""
        def visit_Expr(self, node):
            new = ast.Expr(
                    value = ast.Call(
                        func = ast.Name(id='printExpr', ctx=ast.Load()),
                        args = [node.value], keywords = [])
                    )
            ast.copy_location(new, node)
            ast.fix_missing_locations(new)
            return new

    try:
        module_ast = ast.parse(source)
    except SyntaxError as e:
        return e

    # wrap every expression statement into a print call
    module_ast = ExprPrintWrapper().visit(module_ast)

    return [(ast.Module(body=[n], type_ignores=[]), ast.get_source_segment(source, n))
                    for n in module_ast.body]

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

class PyChunk(Chunk):
    def __init__(self, node, sourceChunk, filename, prevChunk,
                 outputManager=None):
        assert not prevChunk or isinstance(prevChunk, PyChunk) \
                or isinstance(prevChunk, DummyInitialChunk)

        self.node = node
        self.codeObject = None
        self.filename = filename

        super().__init__(sourceChunk, prevChunk, outputManager)

        # all chunks -- of the same "execution chain" / ChunkManager -- share
        # the same globalState. Only for the DummyInitialChunk
        # (-> prevChunk is None) a new StateWrapper is created -- and shared
        # with all other chunks
        self.globalState = prevChunk.globalState \
                            if not isinstance(prevChunk, DummyInitialChunk) \
                            else GlobalsWrapper()
        self.namespace = None

    @property
    def lineRange(self):
        assert self.node
        return range(self.node.body[0].lineno, self.node.body[0].end_lineno + 1)

    def update(self, node):
        self.node = node

    def prepareNamespace(self):
        # derive namespace from prevChunk
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


        # set our local namespace as "global namespace". This needs to be
        # wrapped, because all function objects contain a reference to the
        # global namespace (at chunk execution time! -> func.__globals__).
        # But since we want it to run on this chunks globals, we need a
        # wrapper to exchange the global namespace under the hood
        self.globalState.setData(self.namespace)

    def executeWithCapture(self):
        assert self.codeObject
        assert self.namespace != None

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

        # and execute the chunk and capture stdout
        with dill.temp.capture() as stdoutBuffer:
            error = None
            try:
                exec(self.codeObject, self.globalState)
            except Exception:
                _, _, tb = sys.exc_info()
                error = (traceback.extract_tb(tb)[-1][1],
                         traceback.format_exc())

        del self.namespace['printExpr']

        return stdoutBuffer.getvalue(), dict(printOutputs), error

    def execute_impl(self):
        # compile code if it's the first time we execute this chunk'
        if not self.codeObject or not config.reuseCodeObjects:
            self.codeObject = compile(self.node, self.filename, 'exec')

        # store the sys.modules before we execute this chunk
        beforeModules = set([m for m in sys.modules.keys()])

        self.prepareNamespace()

        self.stdout, self.vtexts, error = self.executeWithCapture()

        if error:
            self.stdout += '\n' + error[1]
            self.vtexts[error[0]] = self.vtexts.get(error[0], [])
            self.vtexts[error[0]].append(error[1])


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

        return error == None
