import re

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
        m = super(MonthNumberToken, self).match(token)
        return m and 1 <= int(m.group(1)) <= 12

def read_grammar(filename="timex-grammar.txt"):
    with open(filename) as f:
        return parse_grammar_spec(f.readline, "timex", globals())

def normalize_space(s):
    """Replace all runs of whitespace with a single space."""
    return " ".join(re.split(r"\s+", s))

def sentences(s):
    """Given a string of English text with normalized spacing (i.e., exactly
    one space between words), yield sentences of that string, one at a time."""
    i, j, n = 0, 0, len(s)
    while j < n:
        if s[j] in ".?!":
            try:
                if s[j+1] == " " and s[j+2].isupper():
                    # Punctuation that is immediately followed by a space
                    # and an upper-case letter is assumed to mark the end
                    # of a sentence. This simple heuristic works most of
                    # the time, but will be fooled by abbreviations.
                    yield s[i:j+1]
                    i = j = j + 2
                    continue
            except IndexError:
                pass
        j += 1
    if i < n and i < j:
        yield s[i:j]

def parse_sentence(sentence, grammar=read_grammar()):
    parser = Parser(grammar)
    toks = sentence.replace("-", " ").split(" ")
    while toks:
        parser.parse(toks)
        try:
            tree = parser.parses().next()
            yield parser.grammar.eval(tree)
            del toks[0:len(list(tree.leaves()))]
        except StopIteration:
            yield toks.pop(0)

