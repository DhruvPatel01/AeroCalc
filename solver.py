import pprint

from ply import lex, yacc
import sympy

import state

def solve(to_solve):
    import parsing

    known = {sympy.symbols(v) for v in state.variables}
    unknown = {sympy.symbols(v) for v in to_solve if v not in state.variables}
    if not unknown:
        print("All variables are known. Delete the variables to force computation.")
        return 1 # One solution already exists
    
    visited_vars = set()
    visited_exprs = set()
    stack = list(unknown)
    current_vars = set(stack)

    while stack:
        x = stack.pop()
        if x in visited_vars:
            continue

        if x in state.var2eqns:
            for expr in state.var2eqns[x]:
                if expr in visited_exprs:
                    continue
                
                visited_exprs.add(expr)
                for var in expr.free_symbols:
                    if (var in known or 
                      var in current_vars or 
                      var in visited_vars):
                        continue
                    stack.append(var)
                    current_vars.add(var)

        current_vars.remove(x)
        visited_vars.add(x)
    
    visited_vars = list(visited_vars)
    visited_exprs = list(visited_exprs)
    print(visited_vars, visited_exprs)
    sol_set = sympy.solve(visited_exprs, visited_vars, dict=True)
    n_sols = len(sol_set)
    lexer = lex.lex(module=parsing)
    parser = yacc.yacc(module=parsing)
    
    for i, sol in enumerate(sol_set[::-1]):
        for v, e in sol.items():
            v = str(v)
            if i > 0:
                v = v + '_{}'.format(i)
            e = v + ' = ' + str(e).replace('**', '^') + ';'
            parser.parse(e, lexer=lexer)
            
                

    return n_sols
        
