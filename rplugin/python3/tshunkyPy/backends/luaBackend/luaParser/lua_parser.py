'''The grammar is 'copy&paste' (c -> python) from
Johan Bjäreholt - lua-compiler
https://github.com/johan-bjareholt/lua-compiler/blob/master/src/grammar.yy
unlicensed.....
'''

from .lua_lexer import *
from ply.yacc import yacc
from ply.lex import lex

def p_block(p):
    '''block	: chunk'''
    p[0] = p[1]

def p_chunk(p):
    '''chunk	: chunk2 laststat
                | chunk2
                | laststat'''
    p[0] = p[1]
    if len(p) > 2:
        p[0] += p[2]

def p_chunk2(p):
    '''chunk2	: stat optsemi
	   	        | chunk stat optsemi '''
    if len(p) == 3:
        p[0] = [p[1]]
    else:
        assert len(p) == 4
        p[0] = p[1] + [p[2]]

def p_optsemi(_):
    '''optsemi	: ';'
                | empty'''
    pass

def p_laststa(p):
    '''laststat : RETURN explist optsemi
                | RETURN optsemi
                | BREAK optsemi'''
    p[0] = [(p.lineno(0), p.lexpos(0))]

def p_stat(p):
    '''stat	: varlist '=' explist
            | LOCAL namelist '=' explist
            | LOCAL namelist
            | FUNCTION funcname funcbody
            | LOCAL FUNCTION name funcbody
            | functioncall
            | DO block END
            | WHILE exp DO block END
            | REPEAT block UNTIL exp
            | if elseiflist else END
            | FOR name '=' exp ',' exp DO block END
            | FOR name '=' exp ',' exp ',' exp DO block END
            | FOR namelist IN explist DO block END'''
    p[0] = (p.lineno(0), p.lexpos(0))

def p_if(_):
    '''if		: IF exp THEN block'''
    pass

def p_elseiflis(_):
    '''elseiflist : elseif
                | elseiflist elseif
                | empty'''
    pass

def p_elseif(_):
    '''elseif	: ELSEIF exp THEN block'''
    pass

def p_else(_):
    '''else	: ELSE block
            | empty'''
    pass

def p_var	(_):
    '''var		: name
                | prefixexp '[' exp ']'
                | prefixexp '.' name'''
    pass

def p_varlist(_):
    '''varlist	: var
            | varlist ',' var'''
    pass

def p_name(_):
    '''name	: IDENTIFIER'''
    pass

def p_funcname(_):
    '''funcname : funcname2
            | funcname2 ':' name'''
    pass

def p_funcname2(_):
    '''funcname2 : name
            | funcname2 '.' name'''
    pass

def p_namelist(_):
    '''namelist : name
            | namelist ',' name'''
    pass

def p_exp(_):
    '''exp		: NIL
            | FALSE
            | TRUE
            | NUMBER
            | string
            | TDOT
            | function
            | prefixexp
            | tableconstructor
            | op'''
    pass

def p_explist(_):
    '''explist	: exp
            | explist ',' exp'''
    pass

def p_prefixexp(_):
    '''prefixexp : var
            | functioncall
            | '(' exp ')' '''
    pass

def p_function(_):
    '''function : FUNCTION funcbody'''
    pass

def p_functioncall(_):
    '''functioncall : prefixexp args
            | prefixexp ':' name args'''
    pass

def p_end(p):
    '''end : END '''
    pass

def p_funcbody(_):
    '''funcbody : '(' parlist ')' block END
            | '(' ')' block END'''
    pass

def p_parlist(_):
    '''parlist	: namelist
            | namelist ',' TDOT
            | TDOT'''
    pass

def p_args(_):
    '''args	: '(' ')'
            | '(' explist ')'
            | tableconstructor
            | string'''
    pass

def p_tableconstructor(_):
    '''tableconstructor : '{' fieldlist '}'
            | '{' '}' '''
    pass

def p_field(_):
    '''field	: '[' exp ']' '=' exp
            | name '=' exp
            | exp'''
    pass

def p_fieldlist(_):
    '''fieldlist : fieldlist2 optfieldsep'''
    pass

def p_fieldlist2(_):
    '''fieldlist2 : field
            | fieldlist2 fieldsep field'''
    pass

def p_optfieldsep(_):
    '''optfieldsep : fieldsep
            | empty'''
    pass

def p_fieldsep(_):
    '''fieldsep : ','
            | ';' '''
    pass

def p_string(_):
    '''string	: STRING'''
    pass

def p_op(_):
    '''op      : op_1'''
    pass

def p_op_1(_):
    '''op_1    : op_1 OR op_2
            | op_2'''
    pass

def p_op_2(_):
    '''op_2    : op_2 AND op_3
            | op_3'''
    pass

def p_op_3(_):
    '''op_3    : op_3 LT op_4
            | op_3 LTE op_4
            | op_3 GT op_4
            | op_3 GTE op_4
            | op_3 NE op_4
            | op_3 EQUALS op_4
            | op_4'''
    pass

def p_op_4(_):
    '''op_4    : op_4 CONCAT op_5
            | op_5'''
    pass

def p_op_5(_):
    '''op_5    : op_5 PLUS op_6
            | op_5 MINUS op_6
            | op_6'''
    pass

def p_op_6(_):
    '''op_6    : op_6 TIMES op_7
            | op_6 DIVIDE op_7
            | op_6 '%' op_7
            | op_7'''
    pass

def p_op_7(_):
    '''op_7    : NOT op_8
            | HASH op_8
            | MINUS op_8
            | op_8'''
    pass

def p_op_8(_):
    '''op_8    : op_8 CIRCUMFLEX op_9
            | op_9'''
    pass

def p_op_9(_):
    '''op_9    : exp'''
    pass

def p_empty(_):
    '''empty : '''
    pass

def p_error(p):
    if p:
        print(f"Syntax error at {p.value}")
        print(p)
    else:
        print("Syntax error at EOF")


def parse(source, filename):
    lexer = lex(debug=False)
    lexer.filename = filename
    parser = yacc(debug=False)
    parser.error = 0
    pos = parser.parse(source, lexer=lexer, tracking=True)
    if parser.error:
        return parser.error

    return pos


