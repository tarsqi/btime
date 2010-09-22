# -*- mode: Python; coding: utf-8 -*-
"""A straightforward implementation of the Earley parsing algorithm."""

__author__ = "Alex Plotnick <plotnick@cs.brandeis.edu>"

import itertools
import sys

from cfg import Terminal, Production, ParseTree

class State(object):
    def __init__(self, rule, start, dot=0, matched=[]):
        self.rule = rule
        self.start = start
        self.dot = dot
        self.matched = matched
        self.complete = (dot == len(rule.rhs)) if dot > 0 else not rule.rhs
        self.next = rule.rhs[dot] if not self.complete else None

    def advance(self, match):
        assert not self.complete, "can't advance a complete state"
        return State(self.rule, self.start, self.dot+1, self.matched + [match])

    def parse_tree(self, tree_class=ParseTree):
        return tree_class(self.rule,
                          [x.parse_tree(tree_class) if isinstance(x, State) \
                                                    else x
                           for x in self.matched])

    def __eq__(self, other):
        return (self.rule == other.rule and
                self.start == other.start and
                self.dot == other.dot)

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash((self.rule, self.start, self.dot))

    def __unicode__(self):
        s = u"[%s →" % self.rule.lhs
        for i in range(len(self.rule)):
            # We should use an interpunct (U+00B7) for the dot, but those
            # tend to be a little light, so we'll use a bullet instead.
            s += u"%s%s" % (u"•" if i == self.dot else " ",
                            self.rule.rhs[i])
        if self.complete: s += u"•"
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
        try:
            return self.chart[i]
        except IndexError:
            # It's not worth checking that i == len(self.chart); we'll just
            # assume it. If it's not, another IndexError will be raised.
            self.chart.append([])
            self.state_cache.append({})
            return self.chart[i]

    def __len__(self):
        return len(self.chart)

    def complete(self, state, i):
        for prev in self[state.start][:]:
            if not prev.complete and prev.next == state.rule.lhs and \
               (prev.rule, prev.start, prev.dot+1) not in self.state_cache[i]:
                self.chart[i].append(prev.advance(state))
                self.state_cache[i][(prev.rule, prev.start, prev.dot+1)] = True

    def predict(self, state, i):
        for rule in self.grammar[state.next]:
            if (rule, i, 0) not in self.state_cache[i]:
                self.chart[i].append(State(rule, i, 0))
                self.state_cache[i][(rule, i, 0)] = True

    def scan(self, state, i, token):
        if state.next.match(token):
            self[i+1] # touch and maybe extend
            entry = (state.rule, state.start, state.dot+1)
            if entry not in self.state_cache[i+1]:
                self.chart[i+1].append(state.advance(token))
                self.state_cache[i+1][entry] = True

    def parse(self, input):
        self.chart = [[State(Production(self.start, self.grammar.start), 0)]]
        self.state_cache = [{}]

        # We have n+1 state sets to process, so we tack on an extra dummy
        # token to the input.
        for i, token in enumerate(itertools.chain(input, [None])):
            for state in self[i]:
                if state.complete:
                    self.complete(state, i)
                elif isinstance(state.next, Terminal):
                    self.scan(state, i, token)
                else:
                    self.predict(state, i)

    def parses(self, tree_class=ParseTree):
        """Yield the completed parse trees."""
        for i in reversed(range(len(self))):
            for state in self[i]:
                if state.rule.lhs is self.start and \
                   state.complete and \
                   state.start == 0:
                    # We skip the inserted start rule by grabbing the first
                    # child matched in the start state.
                    yield state.matched[0].parse_tree(tree_class)

    def pprint(self):
        for i in range(len(self)):
            print "S[%d]:" % i
            for state in self[i]:
                print u"  %s" % state
            print

def parse(input, grammar):
    parser = Parser(grammar)
    parser.parse(input)
    return parser.parses()
