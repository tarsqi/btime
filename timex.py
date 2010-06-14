from datetime import date

from cfg import *
from earley import Parser
from grammarparser import parse_grammar_spec

class Day(object):
    pattern = re.compile("([0-9]{1,2})")

    def __init__(self, day):
        if isinstance(day, basestring):
            m = self.pattern.match(day)
            day = int(m.group(1)) if m else 0
        if not 1 <= day <= 31:
            raise ValueError("invalid day of month: %d" % day)
        self.day = day

class Month(object):
    def __init__(self, month):
        if isinstance(month, basestring):
            month = int(month)
        if not 1 <= month <= 12:
            raise ValueError("invalid month: %d" % month)
        self.month = month

class DayOfMonth(Regexp):
    def __init__(self):
        super(DayOfMonth, self).__init__(r"([0-9]{1,2})(st|nd|rd|th)?$", "day")

    def match(self, token):
        m = super(DayOfMonth, self).match(token)
        return m and 1 <= int(m.group(1)) <= 31

class MonthNumber(Regexp):
    def __init__(self):
        super(MonthNumber, self).__init__(r"([0-9]{1,2})$", "month")

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
