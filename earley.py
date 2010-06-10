"""A straightforward implementation of the Earley parsing algorithm."""

__author__ = "Alex Plotnick <plotnick@cs.brandeis.edu>"

import itertools
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

class Regexp(Terminal):
    def __init__(self, pattern, name=None):
        self.pattern = re.compile(pattern)
        self.name = name or pattern

    def match(self, token):
        return self.pattern.match(token)

    def __str__(self):
        return self.name

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
        return u"%s \u2192 %s" % (self.lhs, u" ".join(map(unicode, self.rhs)))

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
                raise ValueError("Invalid production/action pair")
        super(AttributeGrammar, self).__init__(productions, start)

    def action(self, production):
        return self.actions.get(production, default_action)

    def eval(self, parse):
        if isparsetree(parse):
            rule, children = parse
            return self.action(rule)(map(lambda x: self.eval(x), children))
        else:
            return parse

def isparsetree(x):
    return (isinstance(x, tuple) and
            len(x) == 2 and
            isinstance(x[0], Production))

class State(object):
    def __init__(self, rule, start, dot=0, matched=[]):
        self.rule = rule
        self.start = start
        self.dot = dot
        self.matched = matched

    def peek(self):
        return self.rule.rhs[self.dot]

    def advance(self, matched):
        assert not self.iscomplete(), "can't advance a complete state"
        return State(self.rule, self.start, self.dot+1,
                     self.matched + [matched])

    def iscomplete(self):
        return self.dot == len(self.rule)

    def parse_tree(self):
        return (self.rule,
                [x.parse_tree() if isinstance(x, State) else x
                 for x in self.matched])

    def __eq__(self, other):
        return (isinstance(other, self.__class__) and
                self.rule == other.rule and
                self.start == other.start and
                self.dot == other.dot)

    def __ne__(self, other):
        return not (self == other)

    def __unicode__(self):
        s = u"[%s \u2192" % self.rule.lhs
        for i in range(len(self.rule)):
            # We should use an interpunct (U+00B7) for the dot, but those
            # tend to be a little light, so we'll use a bullet instead.
            s += u"%s%s" % (u"\u2022" if i == self.dot else " ",
                            self.rule.rhs[i])
        if self.iscomplete(): s += u"\u2022"
        s += u", %d]" % self.start
        return s

    if sys.version_info > (3, 0):
        __str__ = __unicode__

class Parser(object):
    """An Earley parser for a given context-free grammar."""

    class StartSymbol(object):
        """We'll need a new start rule for the initial state set; using a
        new instance of a class like this ensures that there will never be
        a conflict with an existing grammar."""
        def __str__(self): return "$"

    def __init__(self, grammar):
        self.grammar = grammar
        self.start = self.StartSymbol()

    def __getitem__(self, i):
        if i == len(self.chart):
            self.chart.append([])
        return self.chart[i]

    def __len__(self):
        return len(self.chart)

    def push_state(self, state, i):
        if state not in self[i]:
            self[i].append(state)
            self.more = True

    def complete(self, state, i):
        for prev in self[state.start][:]:
            if not prev.iscomplete() and prev.peek() == state.rule.lhs:
                self.push_state(prev.advance(state), i)

    def predict(self, state, i):
        for rule in self.grammar[state.peek()]:
            self.push_state(State(rule, i), i)

    def scan(self, state, i, token):
        if state.peek().match(token):
            self.push_state(state.advance(token), i+1)

    def parse(self, input):
        self.chart = [[State(Production(self.start, self.grammar.start), 0)]]

        # We have n+1 state sets to process, so we tack on an extra dummy
        # token to the input.
        for i, token in enumerate(itertools.chain(input, [None])):
            self.more = True
            while self.more:
                # The `more' flag will be set to true when and only when a
                # new state is added via push_state.
                self.more = False
                for state in self[i][:]:
                    if state.iscomplete():
                        self.complete(state, i)
                    elif isinstance(state.peek(), Terminal):
                        self.scan(state, i, token)
                    else:
                        self.predict(state, i)

    def completed_parses(self):
        for i in reversed(range(len(self))):
            for state in self[i]:
                if state.rule.lhs is self.start and \
                   state.iscomplete() and \
                   state.start == 0:
                    yield state.matched[0] # skip inserted start rule

    def pprint(self):
        for i in range(len(self)):
            print "S[%d]:" % i
            for state in self[i]:
                print u"  %s" % state
            print

def parse(input, grammar):
    return Parser(grammar).parse(input)

if __name__ == "__main__":
    def make_productions(spec):
        """Given a specification of grammar rules as a dictionary, produce
        the corresponding productions. Keys are the LHS of the rules; values
        are either a list of alternative RHS, or a single RHS."""
        for lhs, rhs in spec.items():
            if isinstance(rhs, list):
                for alt in rhs:
                    yield Production(lhs, alt)
            else:
                yield Production(lhs, rhs)

    # This example is from the Wikipedia entry for "Earley parser".
    grammar = Grammar(make_productions({"P": "S",
                                        "S": [("S", Literal("+"), "M"), "M"],
                                        "M": [("M", Literal("*"), "T"), "T"],
                                        "T": Regexp("^\d+$", "number")}),
                      start="P")
    parser = Parser(grammar)
    parser.parse("2+3*4")
    parser.pprint()
