import math

import numpy as np
from ply import lex, yacc
import sympy
from astropy import units as u
from astropy.units import imperial as imp

import state
import importer
import solver
import funcs


def string_to_unit(s):
    for module in [u, imp]:
        if hasattr(module, s) and isinstance(getattr(module, s), u.UnitBase):
            return True, getattr(module, s)
    return False, None


keywords = {
    'del': 'DEL',
    'in': 'IN',
    'si': 'SI',
    'variables': 'VARIABLES',
    'reset': 'RESET',
    'solve': 'SOLVE',
    'import': 'IMPORT',
    'eq': 'EQUATION',
}

tokens = [
    'UNIVARIATE_FN',
    'FLOAT',
    'STRING',
    'RAWSTR',
]

tokens = tokens + list(keywords.values())

states = [
    ('raw', 'exclusive')
]

literals = ['/', '*', '+', '-', '(', ')', '=', '^', ';', ',']

def t_FLOAT(t):
    r'(\d+\.\d*) | (\d*\.\d+) | \d+'
    t.value = float(t.value)
    return t

def t_STRING(t):
    r'[a-zA-Z_0-9\.]+'
    if t.value in funcs.univariate_funcs:
        t.type = 'UNIVARIATE_FN'
    else:
        t.type = keywords.get(t.value, 'STRING')
    
    if t.type == 'EQUATION' or t.type == 'IMPORT':
        t.lexer.begin('raw')
    return t

def t_raw_RAWSTR(t):
    r'[^;]+'
    t.lexer.begin('INITIAL')
    return t
    
t_INITIAL_raw_ignore = ' \t'
t_ignore_COMMENT = r'\#.*'

def t_INITIAL_raw_error(t):
    print("Illegal character '%s'" % t.value[0])
    t.lexer.skip(1)

precedence = (
    ('nonassoc', 'IN'),
    ('left', '+', '-'),
    ('left', '*', '/'),
    ('right', 'UMINUS'),
    ('right', 'UPLUS'),
    ('right', '^')
)

def p_start_statement(p):
    '''start : statement
             | command ';'
             | command 
             |
    '''
    pass


def p_start_command(p):
    '''command : DEL STRING
               | VARIABLES
               | IMPORT RAWSTR 
               | RESET
               | SOLVE to_solve
               | EQUATION RAWSTR'''
    if p[1] == 'del':
        if p[2] in state.variables:
            state.variables.pop(p[2])
    elif p[1] == 'variables':
        print(state.variables)
    elif p[1] == 'import':
        importer.do_import(p[2])
    elif p[1] == 'reset':
        state.reset()
    elif p[1] == 'solve':
        n_sols = solver.solve(p[2])
        print(f"\nFound {n_sols} sets of solutions!")
        for i in range(n_sols):
            print(f"Solution #{i}")
            for v in p[2]:
                if i > 0:
                    v = v + '_{}'.format(i)
                print(v, '=', state.variables[v])
            print()
    elif p[1] == 'eq':
        expr = sympy.sympify(p[2])
        state.expressions.add(expr)
        for var in expr.free_symbols:
            state.var2eqns[var].add(expr)


def p_to_solve(p):
    '''to_solve : STRING
                | to_solve ',' STRING
    '''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        if p[3] in p[1]:
            p[0] = p[1]
        else:
            p[0] = p[1] + [p[3]]

def p_statement_assign(p):
    '''statement : STRING "=" expression
                 | STRING "=" expression ';'
    '''
    val = p[3]
    if len(p) == 4:
        print(val)
    state.variables[p[1]] = val


def p_statement_expr(p):
    '''statement : expression
                 | expression ';'
    '''
    val = p[1]
    if len(p) == 2:
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
        exponent = p[3].si
        if exponent.unit != u.dimensionless_unscaled:
            raise ValueError(f"Exponent has to be unitless. Found {exponent.unit}")

        operand = p[1].decompose()
        if operand.unit != u.dimensionless_unscaled:
            if not float.is_integer(exponent.value):
                raise ValueError(f"Exponent needs to be integer when argument has units. Found {exponent.value}")
            ans = 1.0
            for _ in range(int(exponent)):
                ans = ans * p[1]
        else:
            ans = math.pow(operand.value, exponent.value) * u.dimensionless_unscaled
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
    if p[1] in state.variables:
        p[0] = state.variables[p[1]]
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
    "expression : UNIVARIATE_FN '(' expression ')' "
    p[0] = getattr(np, p[1])(p[3].decompose())



def p_error(p):
    if p:
        print("Syntax error at '%s'" % p.value)
    else:
        print("Syntax error at EOF")