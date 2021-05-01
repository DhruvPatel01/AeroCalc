"""
This module will be used to store 
variables and state of the running 
session.

DO NOT ADD DEFAULTS HERE.
"""

from collections import defaultdict

variables = {}

expressions = set()

var2eqns = defaultdict(set)

def reset():
    variables.clear()
    expressions.clear()
    var2eqns.clear()
