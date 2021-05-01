#!/bin/env python

import math
import os
import sys

from ply import lex, yacc
from prompt_toolkit import print_formatted_text as print
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory

import parsing

lexer = lex.lex(module=parsing)
parser = yacc.yacc(module=parsing)


if __name__ == "__main__":
    if len(sys.argv) == 2:
        with open(sys.argv[1]) as fin:
            for line in fin:
                yacc.parse(line.strip())
    else:
        session = PromptSession(history=FileHistory(os.path.expanduser('~/.aerocalc_history')))
        while True:
            try:
                s = session.prompt('NotAeroCalc > ')
            except EOFError:
                break
            except KeyboardInterrupt:
                continue

            if not s:
                continue

            try:
                yacc.parse(s)
            except Exception as e:
                print(e)
                pass

