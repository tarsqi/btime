from unittest import *

from cfg import Grammar, Literal, Production, ParseTree
from earley import State, Parser

class TestState(TestCase):
    def setUp(self):
        self.rule = Production("S", ["NP", "VP"])
        self.state = State(self.rule, 0)

    def test_init(self):
        """Test Earley state initialization"""
        self.assertEqual(self.state.rule, self.rule)
        self.assertEqual(self.state.start, 0)
        self.assertEqual(self.state.dot, 0)
        self.failIf(self.state.matched)
        self.failIf(self.state.complete)
        self.assertEqual(self.state.next, self.rule.rhs[0])

    def test_equal(self):
        """Test Earley state comparison"""
        other = State(self.rule, 0)
        self.assertEqual(self.state, other)
        self.assertNotEqual(self.state, other.advance("NP"))

    def test_advance(self):
        """Test Earley state advancement"""
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
        """Accept a valid string"""
        input = "ab"
        self.parser.parse(input)
        self.assertEqual(len(self.parser), len(input)+1)
        self.failUnless(State(self.rule, 0, len(input)) in self.parser[-1])
        self.assertEqual(list(self.parser.parses()),
                         [ParseTree(self.rule, input)])

    def test_reject(self):
        """Reject an invalid string"""
        self.parser.parse("aa")
        self.failIf(list(self.parser.parses()))

def suite():
    return TestSuite([TestLoader().loadTestsFromTestCase(cls) \
                          for cls in TestState, TestParser])

def run(runner=TextTestRunner, **args):
    return runner(**args).run(suite())

if __name__ == "__main__":
    run(verbosity=2)
