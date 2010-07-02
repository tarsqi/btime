# -*- mode: Python; coding: utf-8 -*-

from functools import wraps
from itertools import chain, repeat, izip as zip
import re

from slotmerger import SlotMerger

class StopFormat(Exception):
    pass

class FormatOp(object):
    def format(self, m):
        return False

    def read(self, m):
        raise StopFormat(m)

class Literal(FormatOp):
    def __init__(self, lit):
        self.lit = lit.upper()

    def format(self, m):
        m.stack.append(self.lit)
        return True

    def read(self, m):
        if not self.lit or m.input.startswith(self.lit, m.i):
            m.i += len(self.lit)
            return True

    def __eq__(self, other):
        return ((isinstance(other, basestring) and self.lit == other.upper()) or
                (isinstance(other, self.__class__) and self.lit == other.lit))

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.lit)

class Separator(Literal):
    def format(self, m):
        m.separators.append(self.lit)
        return True

class Designator(Literal):
    pass

class Coerce(Designator):
    def read(self, m):
        """Coerce the element on the top of the stack to a different type."""
        if super(Coerce, self).read(m):
            m.stack[-1] = self.cls(m.stack[-1])

class UTCDesignator(Designator):
    def __init__(self):
        super(UTCDesignator, self).__init__("Z")

    def read(self, m):
        if super(Designator, self).read(m):
            m.stack.append(UTC)

Z = UTCDesignator()

class Element(FormatOp):
    def __init__(self, cls, min=0, max=None, signed=False):
        assert issubclass(cls, TimeUnit)
        self.cls = cls
        self.min = min
        self.max = max
        self.signed = signed
        self.pattern = re.compile("(%s[0-9]{%d,%s})" % \
                                      ("[+-]" if signed else "",
                                       self.min, self.max or ""))

    def format(self, m):
        elt, cls = m.input.next()
        if elt and issubclass(cls, self.cls):
            value = int(elt)
            m.stack.append((m.separators.pop() if m.separators else "") +
                           (("-" if value<0 else "+") if self.signed else "") +
                           ("%0*d" % (self.min, abs(value)))[0:self.max])
            return True

    def read(self, m):
        match = self.pattern.match(m.input[m.i:])
        if match:
            digits = match.group(0)
            m.stack.append(self.cls(int(digits), signed=self.signed))
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
        if char in self.syntax.designators:
            designate = self.syntax.designators[char]
            if designate and issubclass(designate, TimeUnit):
                # Postfix designator: coerce the last element.
                return Coerce(char, designate)
            elif designate is UTCDesignator:
                return Z
            else:
                if designate:
                    self.stack.append(designate) # push new syntax class
                return Designator(char)

    def separator(self, char):
        for level, cls in enumerate(reversed(self.stack)):
            if char in cls.separators:
                for i in range(level):
                    self.stack.pop()
                return Separator(char)

    def element(self, char):
        """Consume as many of the same digit-representing characters as
        possible from the format representation and return an Element fop."""
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
        return Element(self.syntax.digits[char],
                       n, None if repeat else n, signed)

    @property
    def syntax(self):
        return self.stack[-1]

    def parse(self):
        self.stack = [self.cls] # syntax stack
        for char in self:
            yield (self.designator(char) or
                   self.separator(char) or
                   self.element(char))

class Format(object):
    def __init__(self, cls, format_repr):
        self.cls = cls
        self.ops = list(FormatReprParser(cls, format_repr).parse())

    def format(self, timerep):
        self.separators = []
        self.stack = []
        self.input = iter(timerep)
        ops = iter(self.ops); op = ops.next()
        while True:
            # Fops can decline to format an element; this is used to elide
            # lower-order components.
            if op.format(self):
                try:
                    op = ops.next()
                except StopIteration:
                    break
        return "".join(self.stack)

    def merge_top(self):
        merged = self.stack[-2].merge(self.stack[-1])
        if merged:
            self.stack[-2:] = [merged]
            return merged

    def read(self, string):
        self.input = string.upper()
        self.i = 0
        self.stack = []
        ops = iter(self.ops)
        n = len(self.input)
        while self.i < n:
            ops.next().read(self)
            if len(self.stack) > 1:
                self.merge_top()
        while len(self.stack) > 1:
            if not self.merge_top():
                raise StopFormat(self)
        return self.stack[0]

class InvalidTimeUnit(Exception):
    def __init__(self, unit, value):
        self.unit = unit
        self.value = value

    def __str__(self):
        return "invalid %s: %s" % (self.unit.__class__.__name__.lower(),
                                   self.value)

class TimeUnit(object):
    range = (0,)

    def __init__(self, value, ordinal=True, signed=None,
                 pattern=re.compile(r"([+-])?([0-9]+)")):
        if isinstance(value, basestring):
            m = pattern.match(value)
            if not m:
                raise InvalidTimeUnit(self, value)
            self.signed = m.group(1)
            self.value = int((self.signed if self.signed else "") + m.group(2))
        elif isinstance(value, int):
            self.signed = signed
            self.value = value
        elif isinstance(value, TimeUnit):
            self.signed = value.signed
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

class Year(TimeUnit):
    range = (0, 9999)

    def merge(self, other):
        if isinstance(other, Month):
            return CalendarDate(self, other)
        elif isinstance(other, Week):
            return WeekDate(self, other)
        elif isinstance(other, Day):
            return OrdinalDate(self, other)

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

    def merge(self, other):
        if isinstance(other, Minute):
            if self.signed:
                return UTCOffset(self, other)
            else:
                return Time(self, other)

class Minute(TimeUnit):
    range = (0, 59)

class Second(TimeUnit):
    range = (0, 60) # don't forget leap seconds!

class Cardinal(TimeUnit):
    def __init__(self, value):
        super(Cardinal, self).__init__(value, False)

class Years(Cardinal, Year):
    def merge(self, other):
        if isinstance(other, Months):
            return Duration(self, other)

class Months(Cardinal, Month):
    pass

class Weeks(Cardinal, Week):
    pass

class Days(Cardinal, Day):
    pass

class Hours(Cardinal, Hour):
    def merge(self, other):
        if isinstance(other, Minutes):
            return TimeDuration(self, other)

class Minutes(Cardinal, Minute):
    pass

class Seconds(Cardinal, Second):
    pass

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
        def wrapper(self, *args, **kwargs):
            return method(self, *map(ensure_class, args, units), **kwargs)
        return wrapper
    return ensure_arg_units

class TimeRep(object):
    """Base class for the representations of time points, durations, intervals,
    and recurring intervals."""

    __metaclass__ = SlotMerger
    __mergeslots__ = ["digits", "designators", "separators"]

    digits = {}
    designators = {}
    separators = []

    def __init__(self, elements, element_types):
        self.elements = list(zip(chain(elements, repeat(None)), element_types))

    def __getattr__(self, name):
        for elt, cls in self.elements:
            if any(c.__name__.lower() == name for c in cls.__mro__):
                return elt
        for elt, cls in self.elements:
            if isinstance(elt, TimeRep):
                attr = getattr(elt, name, None)
                if attr:
                    return attr
        raise AttributeError("'%s' representation has no element '%s'" % \
                                 (self.__class__.__name__, name))

    def __iter__(self):
        for elt, cls in self.elements:
            if isinstance(elt, TimeRep):
                for x in elt:
                    yield x
            else:
                yield (elt, cls)

class TimePoint(TimeRep):
    def __init__(self, *args):
        super(TimePoint, self).__init__(*args)

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
        self.reduced_accuracy = lse < len(elements) - 1

class Date(TimePoint):
    digits = {"Y": Year, "M": Month, "D": Day, "w": Week}
    designators = {"W": None} # for week date
    separators = [u"-", # hyphen-minus (a.k.a. ASCII hyphen, U+002D)
                  u"‐"] # hyphen (U+2010)

    def merge(self, other):
        if isinstance(other, Time):
            return DateTime(self, other)
        elif isinstance(other, Hour):
            return DateTime(self, Time(other))

class CalendarDate(Date):
    digits = {"Y": Year, "M": Month, "D": DayOfMonth}

    @units(Year, Month, DayOfMonth)
    def __init__(self, *args):
        self.check_accuracy(*args)
        super(CalendarDate, self).__init__(args, (Year, Month, DayOfMonth))

    def merge(self, other):
        if isinstance(other, Month):
            return CalendarDate(self.year, other)
        elif isinstance(other, Day):
            return CalendarDate(self.year, self.month, other)
        else:
            return super(CalendarDate, self).merge(other)

class OrdinalDate(Date):
    digits = {"Y": Year, "D": DayOfYear}

    @units(Year, DayOfYear)
    def __init__(self, *args):
        self.check_accuracy(*args)
        super(OrdinalDate, self).__init__(args, (Year, DayOfYear))

    def merge(self, other):
        if isinstance(other, Day):
            return OrdinalDate(self.year, other)
        else:
            return super(OrdinalDate, self).merge(other)

class WeekDate(Date):
    digits = {"Y": Year, "w": Week, "D": DayOfWeek}

    @units(Year, Week, Day)
    def __init__(self, *args):
        self.check_accuracy(*args)
        super(WeekDate, self).__init__(args, (Year, Week, Day))

    def merge(self, other):
        if isinstance(other, Week):
            return WeekDate(self.year, other)
        elif isinstance(other, Day):
            return WeekDate(self.year, self.week, other)
        else:
            return super(WeekDate, self).merge(other)

class UTCOffset(TimePoint):
    digits = {"h": Hour, "m": Minute}

    @units(Hour, Minute)
    def __init__(self, hour=0, minute=None):
        self.check_accuracy(hour, minute)
        super(UTCOffset, self).__init__((hour, minute), (Hour, Minute))

UTC = UTCOffset(0)

class Time(TimePoint):
    digits = {"h": Hour, "m": Minute, "s": Second}
    designators = {"T": None, "Z": UTCDesignator}
    separators = [":"]

    @units(Hour, Minute, Second, UTCOffset)
    def __init__(self, hour=None, minute=None, second=None, offset=None):
        self.check_accuracy(hour, minute, second)
        super(Time, self).__init__((hour, minute, second, offset),
                                   (Hour, Minute, Second, UTCOffset))

    def merge(self, other):
        if isinstance(other, Minute):
            return Time(self.hour, other, self.second, self.utcoffset)
        elif isinstance(other, Second):
            return Time(self.hour, self.minute, other, self.utcoffset)
        elif isinstance(other, UTCOffset):
            return Time(self.hour, self.minute, self.second, other)
        elif isinstance(other, Hour) and other.signed:
            return Time(self.hour, self.minute, self.second, UTCOffset(other))

class DateTime(Date, Time):
    designators = {"T": Time}

    @units(Date, Time)
    def __init__(self, date, time):
        self.check_accuracy(date, time)
        TimeRep.__init__(self, (date, time), (Date, Time))

    def merge(self, other):
        if isinstance(other, (Hour, Minute, Second)):
            return DateTime(self.date, self.time.merge(other))
        elif isinstance(other, DateTime):
            return TimeInterval(self, other)

class TimeDuration(TimeRep):
    digits = {"n": TimeUnit}
    designators = {"H": Hours, "M": Minutes, "S": Seconds}

    @units(Hours, Minutes, Seconds)
    def __init__(self, hours=0, minutes=0, seconds=0):
        self.check_accuracy(hours, minutes, seconds)
        super(TimeDuration, self).__init__((hours, minutes, seconds),
                                           (Hours, Minutes, Seconds))

class Duration(TimeRep):
    digits = {"n": TimeUnit}
    designators = {"W": Weeks, "Y": Years, "M": Months, "D": Days,
                   "T": TimeDuration}

    @units(Years, Months, Days, Weeks, TimeDuration)
    def __init__(self, years=0, months=0, days=0, weeks=None, time=None):
        if weeks is not None:
            super(Duration, self).__init__((weeks,), (Weeks,))
        else:
            self.check_accuracy(years, months, days, time)
            super(Duration, self).__init__((years, months, days, time),
                                           (Years, Months, Days, TimeDuration))
class TimeInterval(DateTime):
    designators = {"P": Duration}
    separators = ["/"]

    def __init__(self, *args):
        assert len(args) <= 2, "too many end-points for a time interval"
        self.elements = args
        if len(args) == 1:
            if isinstance(args[0], Duration):
                # a duration and context information (4.4.1 b)
                TimeRep.__init__(self, args, (Duration,))
            else:
                raise ValueError("invalid interval: %s" % (args,))
        else:
            for i, point in (0, "start"), (1, "end"):
                if isinstance(args[i], DateTime):
                    setattr(self, point, args[i])
                else:
                    raise ValueError("invalid interval: %s" % (args,))
            TimeRep.__init__(self, args, map(type, args))

class RecurringTimeInterval(TimeInterval):
    digits = {"n": int}
    designators = {"R": None}

    def __init__(self, n, *args):
        if n is not None and n < 0:
            raise ValueError("invalid number of recurrences %d" % n)
        super(RecurringTimeInterval, self).__init__(*args)
        self.n = n
        # Ack! Kludge! Yuck!
        self.elements = [(self.n, int)] + self.elements
