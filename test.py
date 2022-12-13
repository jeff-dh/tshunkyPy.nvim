import ast

def foo(x):
    print(x)


import time
time.time()
print("blub")
print("aaa")


foo(2)

def foo(x):
    print("!!!")

a = """
if True:
    print("a")
    """

exec(a)

a2 = """
def blub(x):
    print('aaa', x)
    return x
"""

a3 = "1+2+3"

astModule = ast.parse(a2)
astModule.body

astModule2 = ast.parse(a3)
astExpr = astModule2.body
astExpr
v = astExpr[0].value
exp = ast.Expression(v)

astExpr2 = ast.parse(a3, mode='eval')
astExpr2
eval(compile(exp, '...', 'eval'))

#eval(a2)
exec(a2)


res= eval("blub(2)")

print(res)
