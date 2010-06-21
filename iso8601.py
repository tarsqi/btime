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

    designators = []
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
    designators = ["T"]

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

class Duration(object):
    def __init__(self, years=0, months=0, days=0,
                 hours=0, minutes=0, seconds=0,
                 weeks=None):
        if weeks is not None:
            self.weeks = weeks
        else:
            self.years = years
            self.months = months
            self.days = days
            self.hours = hours
            self.minutes = minutes
            self.seconds = seconds

class TimeInterval(object):
    def __init__(self, *args):
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

class RecurringTimeInterval(object):
    def __init__(self, n=None, interval):
        if n is not None and n < 0:
            raise TypeError("invalid number of reccurrences %d" % n)
        if not isinstance(interval, TimeInterval):
            raise TypeError("invalid interval %s" % interval)
        self.n = n
        self.interval = interval

class FormatOp(object):
    pass

class Literal(FormatOp):
    def __init__(self, lit):
        self.value = self.pattern = str(lit)

    def format(self, obj):
        return self.value

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.value == other.value

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, self.value)

class Designator(Literal):
    pass

class Separator(Literal):
    pass

class Element(FormatOp):
    def __init__(self, cls, min=0, max=None, signed=False):
        self.cls = cls
        self.min = min
        self.max = max
        self.signed = signed
        self.pattern = "(%s[0-9]{%d,%s})" % ("[+-]" if signed else "",
                                             self.min, self.max or "")

    def element(self, obj):
        return getattr(obj, self.cls.__name__.lower())

    def format(self, obj):
        value = int(self.element(obj))
        return ((("-" if value < 0 else "+") if self.signed else "") +
                ("%0*d" % (self.min, abs(value)))[0:self.max])

    def __call__(self, value):
        return self.cls(value)

    def __eq__(self, other):
        return (isinstance(other, self.__class__) and
                self.cls is other.cls and
                self.min == other.min and
                self.max == other.max)

    def __repr__(self):
        return "%s(%s, %d, %d, %s)" % (self.__class__.__name__,
                                       self.cls.__name__, self.min, self.max,
                                       self.signed)

def parse_format_repr(cls, format_repr):
    i = peekable(format_repr)
    def getop(c):
        if c in cls.designators:
            return Designator(c)
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
            yield getop(i.next())
    except StopIteration:
        pass

class Format(object):
    def __init__(self, cls, format_repr):
        self.cls = cls
        self.ops = list(parse_format_repr(cls, format_repr))
        self.regex = re.compile("".join([op.pattern for op in self.ops]) + "$")

    def format(self, obj):
        return "".join([op.format(obj) for op in self.ops])

    def read(self, string):
        match = self.regex.match(string)
        if match:
            elements = []
            i = 1
            for op in self.ops:
                if isinstance(op, Element):
                    elements.append(op(int(match.group(i))))
                    i += 1
            return self.cls(*elements)
