# -*- mode: Python; coding: utf-8 -*-
"""Context-free grammars."""

__author__ = "Alex Plotnick <plotnick@cs.brandeis.edu>"

import re
import sys
from types import FunctionType

class Terminal(object):
    """Terminal objects are used to match input tokens. Subclasses should
    override the match method, which takes a token and returns true if that
    token should be considered a match, and false otherwise."""

    def match(self, token):
        return False

class Literal(Terminal):
    def __init__(self, lit):
        self.lit = lit

    def match(self, token):
        return self.lit == token

    def __str__(self):
        return self.lit

class RegexpTerminal(Terminal):
    def __init__(self, pattern, name=None):
        self.pattern = re.compile(pattern)
        self.name = name or pattern

    def match(self, token):
        return token is not None and self.pattern.match(token)

    def __str__(self):
        return self.name

class Acronym(RegexpTerminal):
    def __init__(self, acronym):
        super(Acronym, self).__init__(r"\.?".join(acronym + "$"), acronym)

class Abbrev(Terminal):
    def __init__(self, string, min_prefix_len):
        assert (isinstance(string, basestring) and
                isinstance(min_prefix_len, int) and
                min_prefix_len > 0)
        self.string = string
        self.min = min_prefix_len

    def match(self, token):
        return (len(token) >= self.min and
                self.string.startswith(token.rstrip(".")))

class Production(object):
    """A production rule consists of a left-hand side (LHS) and a
    right-hand side (RHS). A context-free production will have a single
    nonterminal on the LHS. The RHS is a designator for a sequence of
    terminals and nonterminals. Instances should be treated as immutable."""

    def __init__(self, lhs, rhs):
        self.lhs = lhs
        self.rhs = tuple(rhs) if isinstance(rhs, (list, tuple)) else (rhs,)

    def __len__(self):
        return len(self.rhs)

    def __eq__(self, other):
        return (isinstance(other, self.__class__) and
                self.lhs == other.lhs and
                self.rhs == other.rhs)

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash(self.lhs) ^ hash(self.rhs)

    def __repr__(self):
        return "Production(%s, %s)" % (self.lhs, self.rhs)

    def __unicode__(self):
        return u"%s → %s" % (self.lhs, u" ".join(map(unicode, self.rhs)))

    if sys.version_info > (3, 0):
        __str__ = __unicode__

class Grammar(object):
    """A grammar is a collection of production rules and a designated start
    symbol. The list of productions is stored in a dictionary indexed by LHS."""

    def __init__(self, productions, start="S"):
        self.start = start
        self.productions = {}
        for rule in productions:
            if rule.lhs in self.productions:
                self.productions[rule.lhs].append(rule)
            else:
                self.productions[rule.lhs] = [rule]

    def __getitem__(self, lhs):
        return self.productions[lhs]

def default_action(rhs):
    return rhs[0]

class AttributeGrammar(Grammar):
    def __init__(self, productions_and_actions, start="S"):
        productions = []
        self.actions = {}
        for x in productions_and_actions:
            if isinstance(x, tuple) and len(x) == 2:
                rule, action = x
                productions.append(rule)
                if action:
                    assert isinstance(action, FunctionType), \
                        "action must be a function"
                    self.actions[rule] = action
            elif isinstance(x, Production):
                productions.append(x)
            else:
                raise ValueError("Invalid production/action pair: %s" % x)
        super(AttributeGrammar, self).__init__(productions, start)

    def action(self, production):
        return self.actions.get(production, default_action)

    def eval(self, parse):
        if isinstance(parse, ParseTree):
            return self.action(parse.node)(map(lambda x: self.eval(x), parse))
        else:
            return parse

class ParseTree(object):
    def __init__(self, node, children=None):
        self.node = node
        self.children = list(children) if children else None

    def __getitem__(self, index):
        return self.children[index]

    def __eq__(self, other):
        return (isinstance(other, ParseTree) and
                self.node == other.node and
                self.children == other.children)
