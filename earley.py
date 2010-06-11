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
        self.complete = (dot == len(rule))
        self.next = rule.rhs[dot] if not self.complete else None

    def advance(self, match):
        assert not self.complete, "can't advance a complete state"
        return State(self.rule, self.start, self.dot+1,
                     self.matched + [match])

    def parse_tree(self, tree_class=ParseTree):
        return tree_class(self.rule,
                          [x.parse_tree(tree_class) if isinstance(x, State) \
                                                    else x
                           for x in self.matched])

    def __eq__(self, other):
        # N.B.: We should really say self.rule == other.rule, but this
        # method is part of the inner loop, and needs to be fast.
        return (self.rule is other.rule and
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
        if self.complete: s += u"\u2022"
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
            return self.chart[i]

    def __len__(self):
        return len(self.chart)

    def push_state(self, state, i):
        if state not in self[i]:
            self[i].append(state)
            self.more = True

    def complete(self, state, i):
        for prev in self[state.start][:]:
            if not prev.complete and prev.next == state.rule.lhs:
                self.push_state(prev.advance(state), i)

    def predict(self, state, i):
        for rule in self.grammar[state.next]:
            # We could just use push_state here, but this is part of the
            # inner loop, and doing this fast scan over the state set makes
            # a huge difference in performance.
            for state in self[i]:
                if state.rule is rule and state.start == i and state.dot == 0:
                    break
            else:
                self[i].append(State(rule, i))
                self.more = True

    def scan(self, state, i, token):
        if state.next.match(token):
            self.push_state(state.advance(token), i+1)

    def parse(self, input):
        self.chart = [[State(Production(self.start, self.grammar.start), 0)]]

        # We have n+1 state sets to process, so we tack on an extra dummy
        # token to the input.
        for i, token in enumerate(itertools.chain(input, [None])):
            self.more = True
            while self.more:
                # The `more' flag will be set to true only when a new state
                # has been added by the completer, scanner, or predictor.
                self.more = False
                for state in self[i][:]:
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
