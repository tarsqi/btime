# -*- mode: Python; coding: utf-8 -*-

from functools import wraps
import re

from slotmerger import SlotMerger

class StopFormat(Exception):
    pass

class FormatOp(object):
    """FormatOps, or fops, are the operations of a teeny-tiny virtual machine.
    The state of a machine is completely described by a stack of components,
    an input string, and a position in the input."""

    def execute(self, m):
        raise StopFormat(m)

class Literal(FormatOp):
    def __init__(self, lit):
        self.lit = lit.upper()

    def format(self, obj):
        return self.lit

    def execute(self, m):
        if not self.lit or m.input.startswith(self.lit, m.i):
            m.stack.append(self)
            m.i += len(self.lit)
            return True

    def __eq__(self, other):
        return ((isinstance(other, basestring) and self.lit == other.upper()) or
                (isinstance(other, self.__class__) and self.lit == other.lit))

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.lit)

class Separator(Literal):
    def __init__(self, lit, optional, ends):
        super(Separator, self).__init__(lit)
        self.optional = optional
        self.ends = ends

    def execute(self, m):
        if super(Separator, self).execute(m):
            m.stack.pop() # drop separator, maybe temporarily
            for d in self.ends:
                for i, x in enumerate(reversed(m.stack)):
                    if x is d:
                        m.stack[-i-1:] = [d.complete(m.stack[-i:])]
                        break
            if not self.optional:
                m.stack.append(self) # put separator back

    def __repr__(self):
        return "%s(%r, %r, %r)" % (self.__class__.__name__,
                                   self.lit, self.optional, self.ends)

class Designator(Literal):
    """A designator is like a separator in that it matches itself in the
    input string, but it also (usually) indicates a switch to a different
    syntax."""

    def __init__(self, lit, cls=None):
        super(Designator, self).__init__(lit)
        self.syntax_cls = cls

    def execute(self, m):
        if super(Designator, self).execute(m):
            if not self.syntax_cls:
                m.stack.pop() # drop designator

    def complete(self, elts):
        args = [[]]
        for elt in elts:
            if isinstance(elt, Separator) and \
                    elt.lit in self.syntax_cls.separators:
                args.append([])
            else:
                args[-1].append(elt)
        if len(args) == 1:
            args = args[0]
        return self.syntax_cls(*args)

    def __repr__(self):
        return "%s(%r, %s)" % (self.__class__.__name__,
                               self.lit,
                               self.syntax_cls.__name__ if self.syntax_cls
                                                        else None)

class Coerce(Designator):
    """Coerce the element on the top of the stack to a different type."""

    def __init__(self, lit, cls):
        super(Coerce, self).__init__(lit) # no syntax class
        self.coerce = cls

    def execute(self, m):
        if super(Coerce, self).execute(m):
            m.stack.pop() # drop designator
            m.stack[-1] = self.coerce(m.stack[-1])

    def __repr__(self):
        return "%s(%r, %s)" % (self.__class__.__name__,
                               self.lit, self.coerce.__name__)

class Element(FormatOp):
    def __init__(self, cls, min=0, max=None, signed=False):
        self.cls = cls
        self.min = min
        self.max = max
        self.signed = signed
        self.pattern = re.compile("(%s[0-9]{%d,%s})" % \
                                      ("[+-]" if signed else "",
                                       self.min, self.max or ""))

    def element(self, obj):
        return getattr(obj, self.cls.__name__.lower())

    def format(self, obj):
        value = int(self.element(obj))
        return ((("-" if value < 0 else "+") if self.signed else "") +
                ("%0*d" % (self.min, abs(value)))[0:self.max])

    def execute(self, m):
        match = self.pattern.match(m.input[m.i:])
        if match:
            digits = match.group(0)
            m.stack.append(self.cls(int(digits)))
            m.i += len(digits)
            return True

    def __eq__(self, other):
        return (isinstance(other, self.__class__) and
                self.cls is other.cls and
                self.min == other.min and
                self.max == other.max)

    def __repr__(self):
        return "%s(%s, %s, %s, %s)" % (self.__class__.__name__,
                                       self.cls.__name__,
                                       self.min, self.max, self.signed)

class FormatReprParser(object):
    def __init__(self, cls, format_repr):
        self.cls = cls
        self.repr = re.sub(r"_(.)", ur"\1̲", format_repr) # convert _X to X̲

    def __iter__(self):
        self.i = -1
        return self

    def next(self):
        self.i += 1
        try:
            return self.repr[self.i]
        except IndexError:
            raise StopIteration

    def peek(self):
        try:
            return self.repr[self.i+1]
        except IndexError:
            pass

    def designator(self, char):
        """Match a designator in the current syntax, and possibly push a new
        syntax."""
        if char in self.syntax[-1].syntax_cls.designators:
            designated = self.syntax[-1].syntax_cls.designators[char]
            if designated is None:
                # Just a marker: return a new designator, but don't change
                # the syntax.
                 return Designator(char)
            elif issubclass(designated, TimeUnit):
                # Postfix designator: coerce the last element to the given
                # class.
                return Coerce(char, designated)
            else:
                # A true designator: we'll construct an instance of the
                # designated class using elements from the current position
                # to the next separator at a higher syntax level.
                designator = Designator(char, designated)
                self.syntax.append(designator)
                return designator

    def separator(self, char):
        """Match a separator at any syntax level, popping back to that level."""
        for level, syntax in enumerate(reversed(self.syntax)):
            if char in syntax.syntax_cls.separators:
                return Separator(char, syntax.syntax_cls.separators[char],
                                 [self.syntax.pop() for i in range(level)])

    def element(self, char):
        """Consume as many of the same digit-representing characters as
        possible from the input and return an Element fop."""
        signed = False
        if char == u"±":
            signed = True
            char = self.next()
        repeat = False
        n = 1
        while self.peek() == char:
            n += 1
            self.next()
        if self.peek() == u"\u0332": # combining low line (underline)
            repeat = True
            n -= 1 # last char was underlined; don't count it
            self.next() # discard underline
        return Element(self.syntax[-1].syntax_cls.digits[char],
                       n, None if repeat else n, signed)

    def parse(self):
        # Start with an empty designator for the primary syntax class.
        self.syntax = [Designator("", self.cls)]
        yield self.syntax[0]

        for char in self:
            yield (self.designator(char) or
                   self.separator(char) or
                   self.element(char))

        # End with an empty separator that matches all open designators.
        yield Separator("", True,
                        [self.syntax.pop() for i in range(len(self.syntax))])

class Format(object):
    def __init__(self, cls, format_repr):
        self.cls = cls
        self.ops = list(FormatReprParser(cls, format_repr).parse())

    def format(self, obj):
        return "".join([op.format(obj) for op in self.ops])

    def read(self, string):
        self.input = string.upper()
        self.i = 0
        self.stack = []
        ops = iter(self.ops)
        n = len(self.input)
        while self.i < n:
            ops.next().execute(self)
        self.ops[-1].execute(self) # special EOF separator
        return self.stack

class InvalidTimeUnit(Exception):
    def __init__(self, unit, value):
        self.unit = unit
        self.value = value

    def __str__(self):
        return "invalid %s: %s" % (self.unit.__class__.__name__.lower(),
                                   self.value)

class TimeUnit(object):
    range = (0,)

    def __init__(self, value, ordinal=True, pattern=re.compile(r"([0-9]+)")):
        if isinstance(value, basestring):
            m = pattern.match(value)
            if not m:
                raise InvalidTimeUnit(self, value)
            self.value = int(m.group(1))
        elif isinstance(value, int):
            self.value = value
        elif isinstance(value, TimeUnit):
            self.value = value.value
        else:
            raise InvalidTimeUnit(self, value)
        if ordinal and not self.isvalid():
            raise InvalidTimeUnit(self, value)

    def isvalid(self):
        """Check that an ordinal value is within the valid range."""
        if len(self.range) == 1:
            minvalue, = self.range
            return minvalue <= abs(self.value)
        else:
            minvalue, maxvalue = self.range
            return minvalue <= abs(self.value) <= maxvalue

    def __int__(self):
        return self.value

    def __neg__(self):
        return self.__class__(-self.value)

    def __sub__(self, other):
        u"""Naïve subtraction (does not deal with underflow)."""
        if isinstance(other, self.__class__):
            return self.__class__(self.value - other.value)
        elif isinstance(other, int):
            return self.__class__(self.value - other)
        else:
            return NotImplemented

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.value == other.value
        elif isinstance(other, int):
            return self.value == other
        else:
            return NotImplemented

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return self.value != other.value
        elif isinstance(other, int):
            return self.value != other
        else:
            return NotImplemented

    def __lt__(self, other):
        if isinstance(other, self.__class__):
            return self.value < other.value
        elif isinstance(other, int):
            return self.value < other
        else:
            return NotImplemented

    def __hash__(self):
        return self.value

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, self.value)

def ensure_class(obj, cls):
    """Ensure that obj is an instance of cls. If either obj or cls is None,
    that's fine, too."""
    return obj if obj is None or cls is None or isinstance(obj, cls) \
               else cls(obj)

def units(*units):
    """A decorator factory for methods that that need to ensure their arguments
    have the correct units."""
    def ensure_arg_units(method):
        @wraps(method)
        def wrapper(self, *args):
            return method(self, *map(ensure_class, args, units))
        return wrapper
    return ensure_arg_units

class Year(TimeUnit):
    range = (0, 9999)

class Month(TimeUnit):
    range = (1, 12)

class Week(TimeUnit):
    range = (1, 53)

class Day(TimeUnit):
    pass

class DayOfYear(Day):
    range = (1, 366)

class DayOfMonth(Day):
    range = (1, 31)

class DayOfWeek(Day):
    range = (1, 7)

class Hour(TimeUnit):
    range = (0, 24)

class Minute(TimeUnit):
    range = (0, 59)

class Second(TimeUnit):
    range = (0, 60) # don't forget leap seconds!

class TimeRep(object):
    """Base class for the representations of time points, durations, intervals,
    and recurring intervals."""

    __metaclass__ = SlotMerger
    __merge__ = ["digits", "designators", "separators"]

    digits = {}
    designators = {}
    separators = {}

class TimePoint(TimeRep):
    def check_accuracy(self, *elements):
        """Given a list of elements in most-significant-first order, check
        for legitimate omissions. Omission of an element is allowed only if
        all of the more significant elements are supplied."""
        lse = -1
        for i, elt in reversed(tuple(enumerate(elements))):
            if lse >= 0 and not elt:
                raise ValueError("invalid date/time accuracy reduction")
            elif elt and lse < 0:
                lse = i
        if not hasattr(self, "reduced_accuracy"):
            self.reduced_accuracy = False
        self.reduced_accuracy |= lse < len(elements) - 1

class Date(TimePoint):
    digits = {"Y": Year, "M": Month, "D": Day, "w": Week}
    designators = {"W": None} # for week date
    separators = {u"-": True, # hyphen-minus (a.k.a. ASCII hyphen, U+002D)
                  u"‐": True} # hyphen (U+2010)

class CalendarDate(Date):
    digits = {"Y": Year, "M": Month, "D": DayOfMonth}

    @units(Year, Month, DayOfMonth)
    def __init__(self, year, month=None, day=None):
        super(CalendarDate, self).check_accuracy(year, month, day)
        self.year, self.month, self.day = year, month, day

class OrdinalDate(Date):
    digits = {"Y": Year, "D": DayOfYear}

    @units(Year, DayOfYear)
    def __init__(self, year, day=None):
        super(OrdinalDate, self).check_accuracy(year, day)
        self.year, self.day = year, day

class WeekDate(Date):
    digits = {"Y": Year, "w": Week, "D": DayOfWeek}

    @units(Year, Week, Day)
    def __init__(self, year, week=None, day=None):
        super(WeekDate, self).check_accuracy(year, week, day)
        self.year, self.week, self.day = year, week, day

class Time(TimePoint):
    digits = {"h": Hour, "m": Minute, "s": Second}
    designators = {"T": None}
    separators = {":": True}

    @units(Hour, Minute, Second, None)
    def __init__(self, hour, minute=None, second=None, offset=None):
        super(Time, self).check_accuracy(hour, minute, second)
        self.hour, self.minute, self.second = hour, minute, second
        if offset is None or isinstance(offset, UTCOffset):
            self.offset = offset
        else:
            raise TypeError("invalid offset from UTC: %s" % offset)

class UTCOffset(TimePoint):
    digits = {"h": Hour, "m": Minute}

    @units(Hour, Minute)
    def __init__(self, hour=0, minute=None):
        super(UTCOffset, self).check_accuracy(hour, minute)
        self.hour, self.minute = hour, minute

UTC = UTCOffset(0)

class DateTime(Date, Time):
    designators = {"T": Time}

    def __init__(self, *args):
        if isinstance(args[-1], Time):
            time = args[-1]
            args = args[0:-1]
        if any(map(lambda x: isinstance(x, DayOfYear), args)):
            date = OrdinalDate(*args)
            self.__class__ = OrdinalDateTime
            self.__init__(date.year, date.day,
                          time.hour, time.minute, time.second, time.offset)
        elif any(map(lambda x: isinstance(x, Week), args)):
            date = WeekDate(*args)
            self.__class__ = WeekDateTime
            self.__init__(date.year, date.week, date.day,
                          time.hour, time.minute, time.second, time.offset)
        else:
            date = CalendarDate(*args)
            self.__class__ = CalendarDateTime
            self.__init__(date.year, date.month, date.day,
                          time.hour, time.minute, time.second, time.offset)

class CalendarDateTime(DateTime, CalendarDate, Time):
    def __init__(self, year, month=None, day=None,
                 hour=None, minute=None, second=None, offset=None):
        CalendarDate.__init__(self, year, month, day)
        Time.__init__(self, hour, minute, second, offset)

class OrdinalDateTime(DateTime, OrdinalDate, Time):
    def __init__(self, year, day=None,
                 hour=None, minute=None, second=None, offset=None):
        OrdinalDate.__init__(self, year, day)
        Time.__init__(self, hour, minute, second, offset)

class WeekDateTime(DateTime, WeekDate, Time):
    def __init__(self, year, week=None, day=None,
                 hour=None, minute=None, second=None, offset=None):
        WeekDate.__init__(self, year, week, day)
        Time.__init__(self, hour, minute, second, offset)

class TimeDuration(TimeRep):
    digits = {"n": TimeUnit}
    designators = {"H": Hour, "M": Minute, "S": Second}

    @units(Hour, Minute, Second)
    def __init__(self, hours=0, minutes=0, seconds=0):
        self.hours = hours
        self.minutes = minutes
        self.seconds = seconds

class Duration(TimeRep):
    digits = {"n": TimeUnit}
    designators = {"W": Week, "Y": Year, "M": Month, "D": Day,
                   "T": TimeDuration}

    def __init__(self, years=0, months=0, days=0, time=None, weeks=None):
        if weeks is not None:
            self.weeks = weeks
        else:
            self.years = years
            self.months = months
            self.days = days
            self.time = time

class TimeInterval(DateTime):
    designators = {"P": Duration}
    separators = {"/": False}

    def __init__(self, *args):
        self.start = args[0]
        self.end = args[1]
        return

        assert len(args) <= 2
        if len(args) == 1:
            if isinstance(args[0], Duration):
                # 4.4.1 b) a duration and context information
                self.duration = args[0]
            else:
                raise ValueError("invalid interval: %s" % (args,))
        elif isinstance(args[0], DateTime) and isinstance(args[1], DateTime):
            # 4.4.1 a) a start and an end
            self.start, self.end = args
        elif isinstance(args[0], DateTime) and isinstance(args[1], Duration):
            # 4.4.1 c) a start and a duration
            self.start, self.duration = args
        elif isinstance(args[0], Duration) and isinstance(args[1], DateTime):
            # 4.4.1 d) a duration and an end
            self.duration, self.end = args
        else:
            raise ValueError("invalid interval: %s" % (args,))

class RecurringTimeInterval(TimeInterval):
    digits = {"n": int}
    designators = {"R": None}

    def __init__(self, n, *args):
        if n is not None and n < 0:
            raise ValueError("invalid number of recurrences %d" % n)
        self.n = n
        super(RecurringTimeInterval, self).__init__(*args)
