from types import FunctionType
from unittest import *

from earley import Parser
from grammarparser import compile_action, parse_grammar_spec

class CompileActionTest(TestCase):
    def test_expression(self):
        """Compile a single-expression action"""
        action = compile_action(None, "{ _ * 2 }")
        self.failUnless(isinstance(action, FunctionType))
        self.assertEqual(action(2), 4)

    def test_suite(self):
        """Compile an action suite"""
        action = compile_action(None, "{ pass; return _ * 3 }")
        self.failUnless(isinstance(action, FunctionType))
        self.assertEqual(action(2), 6)

    def test_syntax_error(self):
        """Raise syntax error for an invalid action"""
        self.assertRaises(SyntaxError,
                          lambda: compile_action(None, "{ if: else }"))

# Simple arithmetic expressions (from the Wikipedia entry for "Early Parser").
arith_expr_grammar = """
P -> S
S -> S '+' M { _[0] + _[2] }
   | M
M -> M '*' T { _[0] * _[2] }
   | T
T -> r"^\d+$" { int(_[0]) }
"""
def parse_expr(expr, grammar=parse_grammar_spec(arith_expr_grammar, "P")):
    parser = Parser(grammar)
    parser.parse(expr)
    return parser.grammar.eval(parser.parses().next())

class ParseExprTest(TestCase):
    def test_expr(self):
        """Parse simple arithmetic expressions"""
        self.assertEqual(parse_expr("2+3*4"), 14)
        self.assertEqual(parse_expr(["20", "+", "5"]), 25)
        self.assertEqual(parse_expr(["17", "*", "2"]), 34)

# A simple but ambiguous grammar for trivial sentences.
sentence_grammar = """
S -> NP VP { _ }
NP -> NP PP { _ }
NP -> "John"
NP -> "Sue"
NP -> "Denver"
VP -> V NP { _ }
VP -> VP PP { _ }
V -> "called"
PP -> P NP { _ }
P -> "from"
"""
def parse_sentence(sentence, grammar=parse_grammar_spec(sentence_grammar, "S")):
    parser = Parser(grammar)
    parser.parse(sentence.split(" "))
    for parse in parser.parses():
        yield parser.grammar.eval(parse)

class ParseSentenceTest(TestCase):
    def test_unambiguous_sentence(self):
        """Parse an unambiguous sentence"""
        self.assertEqual(list(parse_sentence("John called Sue")),
                         [["John", ["called", "Sue"]]])

    def test_ambiguous_sentence(self):
        """Parse an ambiguous sentence"""
        self.assertEqual(list(parse_sentence("John called Sue from Denver")),
                         [["John", [["called", "Sue"], ["from", "Denver"]]],
                          ["John", ["called", ["Sue", ["from", "Denver"]]]],
                          ["John", ["called", "Sue"]]])

# A rather larger grammer for English cardinals.
number_grammar = """
number -> zero | small | hundreds | thousands
zero -> r"^(zero|oh?|n?[ao]ught)$" { 0 }
small -> ones
    | zero ones { _[1] }
    | teen
    | tens
    | tens ones { _[0] + _[1] }
ones -> "one" { 1 }
    | "two" { 2 }
    | "three" { 3 }
    | "four" { 4 }
    | "five" { 5 }
    | "six" { 6 }
    | "seven" { 7 }
    | "eight" { 8 }
    | "nine" { 9 }
teen -> "ten" { 10 }
    | "eleven" { 11 }
    | "twelve" { 12 }
    | "thirteen" { 13 }
    | "fourteen" { 14 }
    | "fifteen" { 15 }
    | "sixteen" { 16 }
    | "seventeen" { 17 }
    | "eighteen" { 18 }
    | "nineteen" { 19 }
tens -> "twenty" { 20 }
    | "thirty" { 30 }
    | "forty" { 40 }
    | "fifty" { 50 }
    | "sixty" { 60 }
    | "seventy" { 70 }
    | "eighty" { 80 }
    | "ninety" { 90 }
hundreds -> small "hundred" { _[0] * 100 }
    | small "hundred" small { (_[0] * 100) + _[2] }
    | small "hundred" "and" small { (_[0] * 100) + _[3] }
thousands -> small small { _[0] * 100 + _[1] }
    | small "thousand" { _[0] * 1000 }
    | small "thousand" small { (_[0] * 1000) + _[2] }
    | small "thousand" "and" small { (_[0] * 1000) + _[3] }
    | small "thousand" hundreds { (_[0] * 1000) + _[2] }
    | hundreds "thousand" { _[0] * 1000 }
    | hundreds "thousand" small { (_[0] * 1000) + _[2] }
    | hundreds "thousand" "and" small { (_[0] * 1000) + _[3] }
    | hundreds "thousand" hundreds { (_[0] * 1000) + _[2] }
"""

def parse_number(number, grammar=parse_grammar_spec(number_grammar, "number")):
    parser = Parser(grammar)
    parser.parse(number.replace("-", " ").split(" "))
    return parser.grammar.eval(parser.parses().next())

class ParseNumberTest(TestCase):
    def assertNumber(self, number, value):
        self.assertEqual(parse_number(number), value)

    def test_small_numbers(self):
        """Parse numbers x <= 20"""
        for i, s in enumerate(["zero", "one", "two", "three", "four",
                               "five", "six", "seven", "eight", "nine",
                               "ten", "eleven", "twelve", "thirteen",
                               "fourteen", "fifteen", "sixteen", "seventeen",
                               "eighteen", "nineteen", "twenty"]):
            self.assertNumber(s, i)

    def test_tens(self):
        """Parse numbers 20 < x < 100"""
        self.assertNumber("twenty-one", 21)
        self.assertNumber("thirty-two", 32)
        self.assertNumber("forty-three", 43)
        self.assertNumber("fifty-four", 54)
        self.assertNumber("sixty-five", 65)
        self.assertNumber("seventy-six", 76)
        self.assertNumber("eighty-seven", 87)
        self.assertNumber("ninety-eight", 98)

    def test_hundreds(self):
        """Parse numbers 100 <= x < 1000"""
        self.assertNumber("one hundred", 100)
        self.assertNumber("one hundred ten", 110)
        self.assertNumber("one hundred fourteen", 114)
        self.assertNumber("one hundred and thirty-seven", 137)
        self.assertNumber("one hundred eighty", 180)
        self.assertNumber("eight hundred eighty", 880)
        self.assertNumber("twelve hundred thirty-two", 1232)
        self.assertNumber("nineteen hundred ninety-nine", 1999)
        self.assertNumber("eighty-four hundred", 8400)
        self.assertNumber("eighty-four hundred and twelve", 8412)

    def test_thousands(self):
        """Parse numbers 1000 <= x < 1000000"""
        self.assertNumber("one thousand", 1000)
        self.assertNumber("two thousand and one", 2001)
        self.assertNumber("two thousand twelve", 2012)
        self.assertNumber("four thousand one hundred", 4100)
        self.assertNumber("six thousand two hundred sixty-eight", 6268)
        self.assertNumber("twelve thousand nine", 12009)
        self.assertNumber("four hundred thousand nine hundred and one", 400901)

    def test_four_digits(self):
        """Parse four-digit numbers with implicit hundreds"""
        self.assertNumber("seventeen seventy-six", 1776)
        self.assertNumber("nineteen oh one", 1901)
        self.assertNumber("nineteen aught four", 1904)
        self.assertNumber("nineteen ninety-nine", 1999)
        self.assertNumber("twenty o six", 2006)
        self.assertNumber("twenty ten", 2010)

def suite():
    return TestSuite([TestLoader().loadTestsFromTestCase(cls) \
                          for cls in (CompileActionTest,
                                      ParseExprTest,
                                      ParseSentenceTest,
                                      ParseNumberTest)])

def run(runner=TextTestRunner, **args):
    return runner(**args).run(suite())

if __name__ == "__main__":
    run(verbosity=2)
