from decimal import Decimal
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

class MMDDYYyyToken(RegexpTerminal):
    def __init__(self):
        super(MMDDYYyyToken, self).__init__(r"([0-9]{1,2}(/|-)" + \
                                            "[0-9]{1,2}(/|-)" + \
                                            "([0-9]{2}|[0-9]{4}))$",
                                            "MMDDYYyy")

    def match(self, token):
        return super(MMDDYYyyToken, self).match(token)

class MMDDToken(RegexpTerminal):
    def __init__(self):
        super(MMDDToken, self).__init__(r"([0-9]{1,2}(/|-)" + \
                                        "[0-9]{1,2})$",
                                        "MMDD")

    def match(self, token):
        return super(MMDDToken, self).match(token)

class MidToken(RegexpTerminal):
    def __init__(self):
        super(MMDDToken, self).__init__(r"^mid-.*$",
                                        "mid-")

    def match(self, token):
        return super(MMDDToken, self).match(token)
            
class TemporalFunction(object):
    def __call__(self, anchor):
        raise ValueError("invalid temporal function")

    def __str__(self):
        return "%s()" % self.__class__.__name__.upper()

class Now(TemporalFunction):
    def __call__(self, anchor):
        return anchor

class AnchoredInterval(TemporalFunction):
    def __init__(self, duration):
        self.duration = duration

class PastAnchoredInterval(AnchoredInterval):
    def __call__(self, anchor):
        return anchor | self.duration

    def __str__(self):
        return "LAST(%s)" % self.duration

class FutureAnchoredInterval(AnchoredInterval):
    def __call__(self, anchor):
        return self.duration | anchor

    def __str__(self):
        return "NEXT(%s)" % self.duration

class IndefReference(TemporalFunction): pass

class IndefPast(IndefReference): 
    def __str__(self):
        return "INDEF_PAST"

class IndefFuture(IndefReference): 
    def __str__(self):
        return "INDEF_FUTURE"

class TemporalModifier(object):
    def __init__(self, modifier, timex):
        self.modifier = modifier
        self.timex = timex

    def __str__(self):
        return "%s(%s)" % (self.modifier, self.timex)

class Mod(TemporalModifier): pass
class Freq(TemporalModifier): pass
class Quant(TemporalModifier): pass

def read_grammar(filename="timex-grammar.txt"):
    with open(filename) as f:
        return parse_grammar_spec(f.readline, "timex", globals())

def normalize_space(s):
    """Replace all runs of whitespace with a single space."""
    return " ".join(re.split(r"\s+", s))

def mmddyyyy_to_date(token):
    tokens = re.findall(r'\d+', token)
    return CalendarDate(tokens[2], tokens[0], tokens[1])

def mmdd_to_date(token):
    tokens = re.findall(r'\d+', token)
    return MonthDate(tokens[0], tokens[1])

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

def tokenize(sentence):
    """Produce a list of tokens from the given sentence (a string).

    This implementation is dead simple, and is not meant for production use.
    It assumes normalized input."""
    return [word.lower().rstrip(".,;:!")
            for word in sentence.replace("-", " ").split(" ")]

def parse(tokens, grammar=read_grammar()):
    tokens = list(tokens)
    parser = Parser(grammar)
    while tokens:
        parser.parse(tokens)
        try:
            tree = parser.parses().next()
            yield parser.grammar.eval(tree)
            del tokens[0:len(list(tree.leaves()))]
        except StopIteration:
            yield tokens.pop(0)
