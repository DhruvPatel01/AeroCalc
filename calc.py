#!/bin/env python

import math
import os

from ply import lex, yacc
from prompt_toolkit import print_formatted_text as print
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from astropy import units as u
from astropy.units import imperial as imp


def string_to_unit(s):
    if hasattr(u, s) and isinstance(getattr(u, s), u.UnitBase):
        return True, getattr(u, s)
    if hasattr(imp, s) and isinstance(getattr(imp, s), u.UnitBase):
        return True, getattr(imp, s)
    return False, None


keywords = {
    'del': 'DEL',
    'in': 'IN',
    'si': 'SI',
    'variables': 'VARIABLES',
    # 'reset': 'RESET',
    # 'state': 'STATE',
    # 'compute': 'COMPUTE',
    'exp': 'EXP',
    'log': 'LOG',
}

tokens = [
    'FLOAT',
    'STRING',
]

tokens = tokens + list(keywords.values())

literals = ['/', '*', '+', '-', '(', ')', '=', '^']

def t_FLOAT(t):
    r'(\d+\.\d*) | (\d*\.\d+) | \d+'
    t.value = float(t.value)
    return t

def t_STRING(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    t.type = keywords.get(t.value, 'STRING')
    return t

t_ignore = ' \t'

def t_error(t):
    print("Illegal character '%s'" % t.value[0])
    t.lexer.skip(1)

import ply.lex as lex
lexer = lex.lex()

precedence = (
    ('nonassoc', 'IN'),
    ('left', '+', '-'),
    ('left', '*', '/'),
    ('right', 'UMINUS'),
    ('right', 'UPLUS'),
    ('right', '^')
)

# dictionary of names
variables = {}
constants = {}

def p_start_statement(p):
    'start : statement'
    pass


def p_start_command(p):
    '''start : DEL STRING
             | VARIABLES'''
    if p[1] == 'del':
        if p[2] in variables:
            variables.pop(p[2])
    elif p[1] == 'variables':
        print(variables)


def p_statement_assign(p):
    'statement : STRING "=" expression'
    val = p[3]
    print(val)
    variables[p[1]] = val


def p_statement_expr(p):
    'statement : expression'
    val = p[1]
    print(val)


def p_expression_binop(p):
    '''expression : expression '+' expression
                  | expression '-' expression
                  | expression '*' expression
                  | expression '/' expression
                  | expression '^' expression
                  | expression IN expression 
                  | expression IN SI'''
    if p[2] == '+':
        p[0] = p[1] + p[3]
    elif p[2] == '-':
        p[0] = p[1] - p[3]
    elif p[2] == '*':
        p[0] = p[1] * p[3]
    elif p[2] == '/':
        p[0] = p[1] / p[3]
    elif p[2] == '^':
        to_raise = p[3]
        if to_raise.unit != u.dimensionless_unscaled:
            raise ValueError(f"Exponent has to be unitless. Found {to_raise.unit}")

        operand = p[1].decompose()
        if operand.unit != u.dimensionless_unscaled:
            if not float.is_integer(to_raise.value):
                raise ValueError(f"Exponent needs to be integer when argument has units. Found {to_raise.value}")
            ans = 1.0
            for _ in range(int(to_raise)):
                ans = ans * p[1]
        else:
            ans = math.pow(operand.value, to_raise.value) * u.dimensionless_unscaled
        p[0] = ans
    elif p[2] == 'in':
        val = p[1]
        if isinstance(p[3], str) and p[3] == 'si':
            val = val.si
        else:
            val = val.to(p[3], equivalencies=u.temperature())
        p[0] = val
        

def p_expression_uminus(p):
    "expression : '-' expression %prec UMINUS"
    p[0] = -1.0 * p[2]


def p_expression_uplus(p):
    "expression : '+' expression %prec UPLUS"
    p[0] = 1.0 * p[2]


def p_expression_group(p):
    "expression : '(' expression ')'"
    p[0] = p[2]


def p_expression_number(p):
    "expression : FLOAT"
    p[0] = p[1] * u.dimensionless_unscaled


def is_math_const(s):
    if hasattr(math, s) and isinstance(getattr(math, s), (int, float)):
        return True, float(getattr(math, s))
    else:
        return False, None


def p_expression_name(p):
    "expression : STRING"
    if p[1] in variables:
        p[0] = variables[p[1]]
        return

    is_unit, unit = string_to_unit(p[1])
    is_math, math_val = is_math_const(p[1])
    if is_unit:
        p[0] = 1.0 * unit
    elif is_math:
        p[0] = math_val * u.dimensionless_unscaled
    else:
        raise KeyError(f"Lookup for {p[1]} failed.")

    


def p_expression_func(p):
    '''expression : LOG '(' expression ')' 
                  | EXP '(' expression ')'
    '''
    val = p[3]
    if val.unit != u.dimensionless_unscaled:
        raise ValueError(f"Argument to {p[1]} can not have units inside.")
    if p[1] == 'log':
        p[0] = math.log(val.value) * u.dimensionless_unscaled
    elif p[1] == 'exp':
        p[0] = math.exp(val.value) * u.dimensionless_unscaled


def p_error(p):
    if p:
        print("Syntax error at '%s'" % p.value)
    else:
        print("Syntax error at EOF")


if __name__ == "__main__":
    parser = yacc.yacc()
    session = PromptSession(history=FileHistory(os.path.expanduser('~/.aerocalc_history')))

    while True:
        try:
            s = session.prompt('AeroCalc > ')
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

