import ast
import textwrap


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


def wrapLines(lines, width):
    newLines = []
    for l in lines:
        newLines.extend(textwrap.wrap(l, width-1))

    return newLines
