""" Lexer for Lua interpreter

"""

import ply.lex as lex

keywords = {
    "nil": "NIL",
    "return": "RETURN",
    "do": "DO",
    "end": "END",
    "false": "FALSE",
    "true": "TRUE",
    "and": "AND",
    "or": "OR",
    "not": "NOT",
    "while": "WHILE",
    "break": "BREAK",
    "if": "IF",
    "then": "THEN",
    "else": "ELSE",
    "elseif": "ELSEIF",
    "local": "LOCAL",
    "function": "FUNCTION",
    "repeat": "REPEAT",
    "until": "UNTIL",
    "for": "FOR",
    "in": "IN",
}


tokens = [
    'IDENTIFIER',
    'NUMBER',
    'PLUS',
    'MINUS',
    'TIMES',
    'DIVIDE',
    'INTEGER_DIVIDE',
    'LT',
    'GT',
    'LTE',
    'GTE',
    'NE',
    'EQUALS',
    'HASH',
    'CONCAT',
    'TDOT',
    'CIRCUMFLEX',
    'STRING',
]

literals = ["{", "}", "[", "]", "(", ")", '=', ';', ',', '.', '\'', '"', '%']

tokens += keywords.values()

t_PLUS = r'\+'
t_MINUS = r'-'
t_TIMES = r'\*'
t_DIVIDE = r'\/'
t_INTEGER_DIVIDE = r'\/\/'
t_LT = r'<'
t_GT = r'>'
t_LTE = r'<='
t_GTE = r'>='
t_NE = r'~='
t_EQUALS = r'=='
t_HASH = r'\#'
t_CONCAT = r'\.\.'
t_TDOT = r'\.\.\.'
t_CIRCUMFLEX = r'\^'

#copy & paste from https://github.com/eliben/pycparser/blob/master/pycparser/c_lexer.py
#LICENSE: BSD
# simple_escape = r"""([a-wyzA-Z._~!=&\^\-\\?'"]|x(?![0-9a-fA-F]))"""
# decimal_escape = r"""(\d+)(?!\d)"""
# hex_escape = r"""(x[0-9a-fA-F]+)(?![0-9a-fA-F])"""
# bad_escape = r"""([\\][^a-zA-Z._~^!=&\^\-\\?'"x0-9])"""
# escape_sequence = r"""(\\("""+simple_escape+'|'+decimal_escape+'|'+hex_escape+'))'
# escape_sequence_start_in_string = r"""(\\[0-9a-zA-Z._~!=&\^\-\\?'"])"""
# string_char = r"""([^"\\\n]|"""+escape_sequence_start_in_string+')'
# t_STRING = '"'+string_char+'*"' + " | " + "'" +string_char+ "*'"

# copy & past from https://stackoverflow.com/questions/36597386/match-c-strings-and-string-literals-using-regex-in-python
t_STRING = r'(?P<prefix>(?:\bu8|\b[LuU])?)(?:"(?P<dbl>[^"\\]*(?:\\.[^"\\]*)*)"|\'(?P<sngl>[^\'\\]*(?:\\.[^\'\\]*)*)\')|R"([^"(]*)\((?P<raw>.*?)\)\4"'

t_ignore = " \t"

# Tokens = (tok.type, tok.value, tok.lineno, tok.lexpos)
def t_NUMBER(t):
    r'([0-9]*[.][0-9]+)|([0-9]+)'
    if "." in t.value:
        t.value = float(t.value)
        return t
    else:
        t.value = int(t.value)
        return t


def t_IDENTIFIER(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    t.type = keywords.get(t.value, 'IDENTIFIER')    # Check for reserved words
    return t


# Define a rule so we can track line numbers
def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

def t_comment(t):
    r'--[^\n]*'
    pass

def t_error(t):
    print(f"Illegal character {t.value[0]}")
    t.lexer.skip(1)


lexer = lex.lex(debug=False)

if __name__ == "__main__":
    # Test it out
    data = '''
    a = 1
    if 9 >= 2 then
        a = 3
    else
        a = 2
    end

    print(a)
    local function aaa(a, b, c)
        b = 2
        print(b)
    end

    require('blaa').blub()
    require'bla'.foo()
    '''

    # Give the lexer some input
    lexer.input(data)

    # Tokenize
    while True:
        tok = lexer.token()
        if not tok:
            break  # No more input
        print(tok)
