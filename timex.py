from datetime import date

from cfg import *
from earley import Parser
from grammarparser import parse_grammar_spec
from iso8601 import *

class DayOfMonthToken(RegexpTerminal):
    def __init__(self):
        super(DayOfMonthToken, self).__init__(r"([0-9]{1,2})(st|nd|rd|th)?$",
                                              "day of month")

    def match(self, token):
        m = super(DayOfMonthToken, self).match(token)
        return m and 1 <= int(m.group(1)) <= 31

class MonthNumberToken(RegexpTerminal):
    def __init__(self):
        super(MonthNumberToken, self).__init__(r"([0-9]{1,2})$", "month number")

    def match(self, token):
        m = super(MonthNumber, self).match(token)
        return m and 1 <= int(m.group(1)) <= 12

def read_grammar(filename="timex-grammar.txt"):
    with open(filename) as f:
        return parse_grammar_spec(f.readline, "timex", globals())

def parse_timex(timex, grammar=read_grammar()):
    parser = Parser(grammar)
    parser.parse(timex.replace("-", " ").split(" "))
    return parser.grammar.eval(parser.parses().next())
