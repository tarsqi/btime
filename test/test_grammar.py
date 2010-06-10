import unittest

from earley import Parser
from grammarparser import parse_grammar_spec

# Simple arithmetic expressions (from the Wikipedia entry for "Early Parser").
arith_expr_grammar = """
P -> S
S -> S '+' M { _[0] + _[2] }
   | M
M -> M '*' T { _[0] * _[2] }
   | T
T -> Regexp(r"^\d+$", "number") { int(_[0]) }
"""
def parse_expr(expr, grammar=parse_grammar_spec(arith_expr_grammar, "P")):
    parser = Parser(grammar)
    parser.parse(expr)
    return parser.grammar.eval(parser.parses().next())

class ParseExprTest(unittest.TestCase):
    def test_expr(self):
        self.assertEqual(parse_expr("2+3*4"), 14)
        self.assertEqual(parse_expr(["20", "+", "5"]), 25)
        self.assertEqual(parse_expr(["17", "*", "2"]), 34)

# A rather larger grammer for English cardinals.
number_grammar = """
number -> zero | small | hundreds | thousands
zero -> "zero" { 0 }
small -> ones
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
thousands -> small "thousand" { _[0] * 1000 }
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
    parser.parse(number)
    return parser.grammar.eval(parser.parses().next())

class ParseNumberTest(unittest.TestCase):
    def assertNumber(self, number, value):
        self.assertEqual(parse_number(number.replace("-", " ").split(" ")),
                         value)

    def test_small_numbers(self):
        for i, s in enumerate(["zero", "one", "two", "three", "four",
                               "five", "six", "seven", "eight", "nine",
                               "ten", "eleven", "twelve", "thirteen",
                               "fourteen", "fifteen", "sixteen", "seventeen",
                               "eighteen", "nineteen", "twenty"]):
            self.assertNumber(s, i)

    def test_tens(self):
        self.assertNumber("twenty-one", 21)
        self.assertNumber("thirty-two", 32)
        self.assertNumber("forty-three", 43)
        self.assertNumber("fifty-four", 54)
        self.assertNumber("sixty-five", 65)
        self.assertNumber("seventy-six", 76)
        self.assertNumber("eighty-seven", 87)
        self.assertNumber("ninety-eight", 98)

    def test_hundreds(self):
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
        self.assertNumber("one thousand", 1000)
        self.assertNumber("two thousand and one", 2001)
        self.assertNumber("two thousand twelve", 2012)
        self.assertNumber("four thousand one hundred", 4100)
        self.assertNumber("six thousand two hundred sixty-eight", 6268)
        self.assertNumber("twelve thousand nine", 12009)
        self.assertNumber("four hundred thousand nine hundred and one", 400901)

if __name__ == "__main__":
    try:
        unittest.main()
    except SystemExit:
        pass
