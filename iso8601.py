# -*- mode: Python; coding: utf-8 -*-

from functools import wraps
import re

from peekable import peekable
from slotmerger import SlotMerger

class InvalidTimeUnit(Exception):
    def __init__(self, unit, value):
        self.unit = unit
        self.value = value

    def __str__(self):
        return "invalid %s: %s" % (self.unit.__class__.__name__.lower(),
                                   self.value)

class TimeUnit(object):
    range = (0,)

    def __init__(self, value, pattern=re.compile(r"([0-9]+)")):
        if isinstance(value, basestring):
            m = pattern.match(value)
            if not m:
                raise InvalidTimeUnit(self, value)
            super(TimeUnit, self).__setattr__("value", int(m.group(1)))
        elif isinstance(value, int):
            super(TimeUnit, self).__setattr__("value", value)
        else:
            raise InvalidTimeUnit(self, value)
        if not self.isvalid():
            raise InvalidTimeUnit(self, value)

    def isvalid(self):
        minvalue, maxvalue = self.range
        if maxvalue is None:
            return minvalue <= abs(self.value)
        else:
            return minvalue <= abs(self.value) <= maxvalue

    def __setattr__(self, *args):
        raise TypeError("units of time are immutable")

    __delattr__ = __setattr__

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

class TimePoint(object):
    __metaclass__ = SlotMerger
    __merge__ = ["designators", "separators", "digits"]

    designators = {}
    separators = []
    digits = {}

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
    separators = ["-"]

class CalendarDate(Date):
    digits = {"Y": Year, "M": Month, "D": DayOfMonth}

    @units(Year, Month, DayOfMonth)
    def __init__(self, year, month=None, day=None):
        self.year, self.month, self.day = year, month, day
        super(CalendarDate, self).check_accuracy(self.year,
                                                 self.month,
                                                 self.day)

class OrdinalDate(Date):
    digits = {"Y": Year, "D": DayOfYear}

    @units(Year, DayOfYear)
    def __init__(self, year, day=None):
        self.year, self.day = year, day
        super(OrdinalDate, self).check_accuracy(self.year, self.day)

class WeekDate(Date):
    digits = {"Y": Year, "w": Week, "D": DayOfWeek}

    @units(Year, Week, Day)
    def __init__(self, year, week=None, day=None):
        self.year, self.week, self.day = year, week, day
        super(WeekDate, self).check_accuracy(self.year, self.week, self.day)

class Time(TimePoint):
    digits = {"h": Hour, "m": Minute, "s": Second}
    separators = [":"]

    @units(Hour, Minute, Second, None)
    def __init__(self, hour, minute=None, second=None, offset=None):
        self.hour, self.minute, self.second = hour, minute, second
        if offset is None or isinstance(offset, UTCOffset):
            self.offset = offset
        else:
            raise TypeError("invalid offset from UTC: %s" % offset)
        super(Time, self).check_accuracy(self.hour, self.minute, self.second)

class UTCOffset(TimePoint):
    digits = {"h": Hour, "m": Minute}

    @units(Hour, Minute)
    def __init__(self, hour=0, minute=None):
        self.hour, self.minute = hour, minute
        super(UTCOffset, self).check_accuracy(self.hour, self.minute)

UTC = UTCOffset(0)

class DateTime(TimePoint):
    designators = {"T": Time} # XXX

    def __init__(self, date, time):
        assert date is None or isinstance(date, Date)
        assert time is None or isinstance(time, Time)
        self.date = date
        self.time = time
        if time and date and date.reduced_accuracy:
            raise ValueError("can't have time with an incomplete date")
        super(UTCOffset, self).check_accuracy(self.date, self.time)

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

class FormatOp(object):
    pass

class Designator(FormatOp):
    def __init__(self, cls):
        self.cls = cls

    def format(self, obj):
        pass

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, self.cls.__name__)

class Separator(FormatOp):
    def __init__(self, separator):
        self.separator = separator

    def format(self, obj):
        return self.separator

    def read(self, string, start):
        if string[start] == self.separator:
            return (self.separator, start+1)
        else:
            return (None, start)

    def __eq__(self, other):
        return (isinstance(other, self.__class__) and
                self.separator == other.separator)

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, self.sep)

class Element(FormatOp):
    def __init__(self, cls, min=0, max=None, signed=False):
        self.cls = cls
        self.min = min
        self.max = max
        self.signed = signed
        self.pattern = re.compile(("[+-]" if signed else "") +
                                  "[0-9]{%d,%s}" % (self.min, self.max or ""))

    def element(self, obj):
        return getattr(obj, self.cls.__name__.lower())

    def format(self, obj):
        value = int(self.element(obj))
        return ((("-" if value < 0 else "+") if self.signed else "") +
                ("%0*d" % (self.min, abs(value)))[0:self.max])

    def read(self, string, start):
        match = self.pattern.match(string[start:])
        if match:
            digits = match.group(0)
            return (self.cls(int(digits)), start + len(digits))
        else:
            return (None, start)

    def __eq__(self, other):
        return (isinstance(other, self.__class__) and
                self.cls is other.cls and
                self.min == other.min and
                self.max == other.max)

    def __repr__(self):
        return "%s(%s, %d, %d)" % (self.__class__.__name__,
                                   self.cls.__name__, self.min, self.max)

def parse_format_repr(cls, format_repr):
    i = peekable(format_repr)
    def op(c):
        if c in cls.designators:
            return Designator(cls.designators[c])
        elif c in cls.separators:
            return Separator(c)
        elif c == "_":
            return Element(cls.digits[i.next()])
        else:
            signed = False
            if c == u"±":
                signed = True
                c = i.next()
            n = 1
            try:
                while i.peek() == c:
                    n += 1
                    i.next()
                if i.peek() == u"\u0332": # combining low line (underline)
                    i.next() # discard underline
                    return Element(cls.digits[c], n-1, None, signed)
                elif i.peek(2) == ["_", c]:
                    i.next(2) # discard underline and char
                    return Element(cls.digits[c], n, None, signed)
            except StopIteration:
                pass
            return Element(cls.digits[c], n, n, signed)
    try:
        while True:
            yield op(i.next())
    except StopIteration:
        pass

class ParseError(Exception):
    def __init__(self, cls, i):
        self.cls = cls
        self.i = i

    def __str__(self):
        return "parse error: %s (char %d)" % (self.cls.__name__, self.i)

class Format(object):
    def __init__(self, cls, format_repr):
        self.cls = cls
        self.ops = list(parse_format_repr(cls, format_repr))

    def format(self, obj):
        return "".join([op.format(obj) for op in self.ops])

    def read(self, string):
        i = 0
        elements = []
        for op in self.ops:
            x, i = op.read(string, i)
            if x is None:
                raise ParseError(self.cls, i)
            elif isinstance(x, TimeUnit):
                elements.append(x)
        return self.cls(*elements)
