from unittest import *

from cfg import Grammar, Literal, Production, ParseTree
from earley import State, Parser

class TestState(TestCase):
    def setUp(self):
        self.rule = Production("S", ["NP", "VP"])
        self.state = State(self.rule, 0)

    def test_init(self):
        self.assertEqual(self.state.rule, self.rule)
        self.assertEqual(self.state.start, 0)
        self.assertEqual(self.state.dot, 0)
        self.failIf(self.state.matched)
        self.failIf(self.state.complete)
        self.assertEqual(self.state.next, self.rule.rhs[0])

    def test_equal(self):
        other = State(self.rule, 0)
        self.assertEqual(self.state, other)
        self.assertNotEqual(self.state, other.advance("NP"))

    def test_advance(self):
        state = self.state.advance("NP")
        self.assertNotEqual(state, self.state)
        self.assertEqual(state.rule, self.rule)
        self.assertEqual(state.start, 0)
        self.assertEqual(state.dot, 1)
        self.assertEqual(state.matched, ["NP"])
        self.failIf(state.complete)
        self.assertEqual(state.next, self.rule.rhs[1])
        
        state = state.advance("VP")
        self.assertEqual(state.matched, ["NP", "VP"])
        self.failUnless(state.complete)
        self.failIf(state.next)
        self.assertRaises(Exception, lambda match: state.advance(match), None)

class TestParser(TestCase):
    def setUp(self):
        self.rule = Production("S", [Literal("a"), Literal("b")])
        self.grammar = Grammar([self.rule])
        self.parser = Parser(self.grammar)

    def test_parse(self):
        input = "ab"
        self.parser.parse(input)
        self.assertEqual(len(self.parser), len(input)+1)
        self.failUnless(State(self.rule, 0, len(input)) in self.parser[-1])
        self.assertEqual(list(self.parser.parses()),
                         [ParseTree(self.rule, input)])

    def test_reject(self):
        self.parser.parse("aa")
        self.failIf(list(self.parser.parses()))

def suite():
    return TestSuite([TestLoader().loadTestsFromTestCase(TestState),
                      TestLoader().loadTestsFromTestCase(TestParser)])

if __name__ == "__main__":
    try:
        TextTestRunner().run(suite())
    except SystemExit:
        pass
