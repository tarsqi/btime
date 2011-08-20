from decimal import Decimal
import re
import codecs

from cfg import *
from earley import Parser
from grammarparser import parse_grammar_spec
from iso8601 import *

# Terminals for the timex grammar.

class DayOfMonthToken(RegexpTerminal):
    def __init__(self):
        super(DayOfMonthToken, self).__init__(r"([0-9]{1,2})(st|nd|rd|th)?$",
                                              "day of month")

    def match(self, token):
        m = super(DayOfMonthToken, self).match(token)
        return m and 1 <= int(m.group(1)) <= 31

class MonthNumberToken(RegexpTerminal):
    def __init__(self):
        super(MonthNumberToken, self).__init__(r"([0-9]{1,2})$",
                                               "month number")

    def match(self, token):
        m = super(MonthNumberToken, self).match(token)
        return m and 1 <= int(m.group(1)) <= 12

class MMDDYYyyToken(RegexpTerminal):
    def __init__(self):
        super(MMDDYYyyToken, self).__init__(
            r"^[0-9]{1,2}(/|-)[0-9]{1,2}(/|-)([0-9]{2}|[0-9]{4})$",
            "MMDDYYyy")

    def match(self, token):
        return super(MMDDYYyyToken, self).match(token)

class MMDDToken(RegexpTerminal):
    def __init__(self):
        super(MMDDToken, self).__init__(r"^[0-9]{1,2}(/|-)[0-9]{1,2}$",
                                        "MMDD")

    def match(self, token):
        return super(MMDDToken, self).match(token)

class HHMMToken(RegexpTerminal):
    def __init__(self):
        super(HHMMToken, self).__init__(r"^[0-2]?\d:[0-5]\d$",
                                        "HHMM")

    def match(self, token):
        return super(HHMMToken, self).match(token)

class HHMMSSToken(RegexpTerminal):
    def __init__(self):
        super(HHMMSSToken, self).__init__(r"^[0-2]?\d:[0-5]\d:[0-5]\d$",
                                          "HHMMSS")

    def match(self, token):
        return super(HHMMSSToken, self).match(token)

class Any(Terminal):
    def match(self, token): return True

class GreaterThan(Terminal):
    def __init__(self, lower_bound):
        self.lower_bound = lower_bound

    def match(self, token):
        try:
            return token > lower_bound
        except Exception:
            return False

class Exact(Terminal):
    """i.e. preserving case when checking for a match."""
    def __init__(self, lit):
        self.lit = unicode(lit)
    
    def match(self, token):
        if not isinstance(token, basestring): return False
        return token and self.lit == unicode(token)

f = codecs.open('timex-grammar.txt', mode='r', encoding='UTF-8')
raw = f.read()
f.close()
literals = set([lit[2:-2] for lit in re.findall(r'\s\"[A-Za-z]*?\"\s', raw)])

class Other(Terminal):
    """Matches strings NOT found in the grammar."""
    def __init__(self): pass

    def match(self, token):
        return token.lower() in literals

# Temporal functions.
            
class TemporalFunction(object):
    def __call__(self, anchor):
        raise ValueError("Not yet implemented for %s" %
                         self.__class__.__name__)

    def __str__(self):
        return "%s()" % self.__class__.__name__

class PastRef(TemporalFunction): pass

class FutureRef(TemporalFunction): pass

class PresentRef(TemporalFunction): pass

class AnchoredTimex(TemporalFunction):
    def __init__(self, timex, tid, anchor_tid):
        self.timex = timex
        self.tid = tid
        self.anchor_tid = anchor_tid

    def __str__(self):
        return "%s(%s, %s, %s)" % (self.__class__.__name__,
                                   self.timex,
                                   self.tid,
                                   self.anchor_tid)

class BeginAnchoredTimex(AnchoredTimex): pass

class EndAnchoredTimex(AnchoredTimex): pass

class Anchor(TemporalFunction):
    def __call__(self, anchor):
        return anchor

class UtteranceTime(Anchor): pass

class ReferenceTime(Anchor): pass

class AnchoredInterval(TemporalFunction):
    def __call__(self, anchor):
        self.anchor = anchor
        return self
        
    def __init__(self, duration):
        self.duration = duration
        self.anchor = None

    def __str__(self):
        if self.anchor:
            return "%s(%s)(%s)" % (self.__class__.__name__,
                                   self.duration,
                                   self.anchor)
        else:
            return "%s(%s)" % (self.__class__.__name__,
                               self.duration)

class PastAnchoredInterval(AnchoredInterval, PastRef): pass

class FutureAnchoredInterval(AnchoredInterval, FutureRef): pass

class IndefReference(TemporalFunction):
    def __init__(self):
        self.anchor = None

    def __call__(self, anchor):
        self.anchor = anchor
        return self

class IndefPast(IndefReference, PastRef): pass

class IndefFuture(IndefReference, FutureRef): pass

class IndefTimePoint(IndefReference): pass

class GenericPlural(TemporalFunction):
    def __init__(self, unit):
        self.unit = unit

    def __str__(self):
        return "%s(%s)" % (self.__class__.__name__, self.unit.__name__)

class AnchoredTimePoint(TemporalFunction):
    def __call__(self, anchor):
        if not (self.anchor and isinstance(self.anchor, TemporalFunction)):
            self.anchor = anchor
        else:
            self.anchor = self.anchor(anchor) 
        return self
    
    def __init__(self, duration):
        self.duration = duration
        self.anchor = None

    def __str__(self):
        if self.anchor:
            return "%s(%s)(%s)" % (self.__class__.__name__,
                                   self.duration,
                                   self.anchor)
        else:
            return "%s(%s)" % (self.__class__.__name__,
                               self.duration)

class PastAnchoredTimePoint(AnchoredTimePoint, PastRef): pass

class FutureAnchoredTimePoint(AnchoredTimePoint, FutureRef): pass

class IncrementOrDecrement(TemporalFunction):
    def __call__(self, anchor):
        if not (self.anchor and isinstance(self.anchor, TemporalFunction)):
            self.anchor = anchor
        else:
            self.anchor = self.anchor(anchor) 
        return self
    
    def __init__(self, unit):
        self.unit = unit
        self.anchor = None

    def __str__(self):
        if self.anchor:
            return "%s(%s)(%s)" % (self.__class__.__name__,
                                   self.unit.__name__,
                                   self.anchor)
        else:
            return "%s(%s)" % (self.__class__.__name__,
                               self.unit.__name__)

class Decrement(IncrementOrDecrement, PastRef): pass

class Increment(IncrementOrDecrement, FutureRef): pass

class NextOrLastInstance(TemporalFunction):
    def __call__(self, anchor):
        if not (self.anchor and isinstance(self.anchor, TemporalFunction)):
            self.anchor = anchor
        else:
            self.anchor = self.anchor(anchor) 
        return self
    
    def __init__(self, timepoint):
        self.timepoint = timepoint
        self.anchor = None

    def __str__(self):
        if self.anchor:
            return "%s(%s)(%s)" % (self.__class__.__name__,
                                   self.timepoint,
                                   self.anchor)
        else:
            return "%s(%s)" % (self.__class__.__name__,
                               self.timepoint)

class NextInstance(NextOrLastInstance, FutureRef): pass

class LastInstance(NextOrLastInstance, PastRef): pass   

class CoercedTimePoint(TemporalFunction):
    def __init__(self, timepoint, unit):
        self.timepoint = timepoint
        self.unit = unit

    def __str__(self):
        return "%s(%s, %s)" % (self.__class__.__name__,
                               self.timepoint,
                               self.unit.__name__)

class TemporalModifier(TemporalFunction):
    def __init__(self, modifier, timex):
        self.modifier = modifier
        self.timex = timex

    def __str__(self):
        return "%s(%s, %s)" % (self.__class__.__name__,
                               self.modifier,
                               self.timex)

class Mod(TemporalModifier): pass

class Freq(TemporalModifier): pass

class Quant(TemporalModifier): pass

class DoNotParse(object):
    """In the grammar, you can use this class to modify objects (i.e.
       anchoring temporal functions) without 'consuming' them - the parse
       method knows to 'flatten' these.""" 
    def __init__(self, dontparse):
        self.dontparse = dontparse

    def __call__(self):
        for x in self.dontparse:
            yield x

def read_timex_grammar(filename="timex-grammar.txt"):
    with open(filename) as f:
        return parse_grammar_spec(f.readline, "timex", globals())

def normalize_space(s):
    """Replace all runs of whitespace with a single space."""
    return " ".join(re.split(r"\s+", s))

def mmddyyyy_to_date(token):
    tokens = re.findall(r'\d+', token)
    year = int(tokens[2])
    if year < 20: year += 2000
    elif year < 100: year += 1900
    return CalendarDate(year, tokens[0], tokens[1])

def mmdd_to_date(token):
    tokens = re.findall(r'\d+', token)
    return MonthDate(tokens[0], tokens[1])

def yyyymmdd_to_date(token):
    return CalendarDate(token[:4], token[4:6], token[6:])

def yymmdd_to_date(token):
    return CalendarDate(token[:2], token[2:4], token[4:])

def hhmmss_to_time(token):
    tokens = re.findall(r'\d+', token)
    return Time(tokens[0], tokens[1], tokens[2])

def hhmm_to_time(token):
    tokens = re.findall(r'\d+', token)
    return Time(tokens[0], tokens[1])

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

def parse(tokens, grammar=read_timex_grammar()):
    tokens = list(tokens)
    parser = Parser(grammar)
    while tokens:
        parser.parse(tokens)
        try:
            tree = parser.parses().next()
            next_parse = parser.grammar.eval(tree)
            if isinstance(next_parse, DoNotParse):
                for p in next_parse():
                    yield p
            else:
                yield next_parse
            del tokens[0:len(list(tree.leaves()))]
        except StopIteration:
            yield tokens.pop(0)

def anchored(timex):
    return timex['anchorTimeID'] or timex['beginPoint'] or timex['endPoint']

def anchor_type(timex):
    if isinstance(timex, Anchor): return type(timex)
    elif isinstance(timex, TemporalModifier):
        return anchor_type(timex.timex)
    elif isinstance(timex, TemporalFunction):
        try:
            return anchor_type(timex.anchor)
        except AttributeError:
            pass

def anchoring_type(timex):
    if timex['anchorTimeID']: return 'ANCHOR'
    elif timex['beginPoint']: return 'BEGIN'
    elif timex['endPoint']: return 'END'

def timex_type(timex):
    if isinstance(timex, TemporalModifier): return timex_type(timex.timex)
    else: return type(timex)

def granularity(timex):
    if not timex: return None
    elif timex.__module__ == 'iso8601.iso8601':
        cls = None
        if isinstance(timex, Duration):
            for unit in timex.elements[::-1]:
                if unit.value:
                    cls = type(unit)
                    break
        else:
            cls = type(timex)
        if not cls: return 'Undefined'
        for timex_type in [Day, Year, Month, Quarter, Week, Hour, Minute,
                           Second, Date]:
            if issubclass(cls, timex_type): return timex_type.__name__
        return 'Undefined'
    elif isinstance(timex, (AnchoredTimex,
                            TemporalModifier)):
        return granularity(timex.timex)
    elif isinstance(timex, (AnchoredInterval,
                            AnchoredTimePoint)):
        return granularity(timex.duration)
    elif isinstance(timex, (GenericPlural,
                            IncrementOrDecrement,
                            CoercedTimePoint)):
        return granularity(timex.unit)
    elif isinstance(timex, NextOrLastInstance):
        return granularity(timex.timepoint)
