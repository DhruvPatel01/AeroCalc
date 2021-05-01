from ply import yacc, lex
import sympy

import state

def do_import(filename):
    import parsing
    lexer = lex.lex(module=parsing)
    parser = yacc.yacc(module=parsing)

    with open(filename) as fin:
        for line in fin:
            line = line.strip()
            parser.parse(line, lexer=lexer)

