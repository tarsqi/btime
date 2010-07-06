# -*- mode: Python; coding: utf-8 -*-

from decimal import Decimal
from functools import wraps
from itertools import chain, repeat, izip as zip
from operator import eq
import re

from slotmerger import SlotMerger

class InvalidTimeUnit(Exception):
    def __init__(self, unit, value):
        self.unit = unit
        self.value = value

    def __str__(self):
        return "invalid %s %r" % (type(self.unit).__name__.lower(), self.value)

class TimeUnit(object):
    """A unit of time."""

    range = (0,)

    def __init__(self, value, ordinal=True, signed=None,
                 pattern=re.compile(r"([+-])?([0-9]+)")):
        if isinstance(value, basestring):
            m = pattern.match(value)
            if not m:
                raise InvalidTimeUnit(self, value)
            self.signed = m.group(1)
            self.value = int((self.signed if self.signed else "") + m.group(2))
        elif value is None or isinstance(value, (int, Decimal)):
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
        if self.value is None:
            return True # None is always a valid value
        if len(self.range) == 1:
            minvalue, = self.range
            return minvalue <= abs(self.value)
        else:
            minvalue, maxvalue = self.range
            return minvalue <= abs(self.value) <= maxvalue

    def merge(self, other):
        return self or other

    def __int__(self):
        return self.value

    def __nonzero__(self):
        return self.value is not None

    def __neg__(self):
        return type(self)(-self.value)

    def __sub__(self, other):
        u"""Naïve subtraction (does not deal with underflow)."""
        if isinstance(other, type(self)):
            return type(self)(self.value - other.value)
        elif isinstance(other, (int, Decimal)):
            return type(self)(self.value - other)
        else:
            return NotImplemented

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return self.value == other.value
        elif isinstance(other, (int, Decimal)):
            return self.value == other
        else:
            return NotImplemented

    def __ne__(self, other):
        if isinstance(other, type(self)):
            return self.value != other.value
        elif isinstance(other, (int, Decimal)):
            return self.value != other
        else:
            return NotImplemented

    def __lt__(self, other):
        if isinstance(other, type(self)):
            return self.value < other.value
        elif isinstance(other, (int, Decimal)):
            return self.value < other
        else:
            return NotImplemented

    def __hash__(self):
        return self.value

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return "%s(%r)" % (type(self).__name__, self.value)

unit = TimeUnit(None)

class Year(TimeUnit):
    range = (0, 9999)

    def merge(self, other, destructive=False):
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

    def merge(self, other, destructive=False):
        if isinstance(other, Minute):
            if self.signed:
                return UTCOffset(self, other)
            else:
                return Time(self, other)
        elif isinstance(other, UTCOffset):
            return Time(self, None, None, other)

class Minute(TimeUnit):
    range = (0, 59)

class Second(TimeUnit):
    range = (0, 60) # don't forget leap seconds!

class Cardinal(TimeUnit):
    def __init__(self, value, signed=False):
        if value is not None and value < 0:
            raise ValueError("invalid cardinal %r" % value)
        super(Cardinal, self).__init__(value, signed)

class Years(Cardinal, Year):
    def merge(self, other, destructive=False):
        if isinstance(other, Months):
            return Duration(self, other)

class Months(Cardinal, Month):
    pass

class Weeks(Cardinal, Week):
    pass

class Days(Cardinal, Day):
    pass

class Hours(Cardinal, Hour):
    def merge(self, other, destructive=False):
        if isinstance(other, Minutes):
            return TimeDuration(self, other)

class Minutes(Cardinal, Minute):
    pass

class Seconds(Cardinal, Second):
    pass

class Recurrences(Cardinal):
    pass

def ensure_class(obj, cls):
    """Ensure that obj is an instance of cls. If cls is None, skip the check."""
    return obj if cls is None or isinstance(obj, cls) \
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

class TimeRep(object):
    """Base class for the representations of time points, durations, intervals,
    and recurring intervals."""

    __metaclass__ = SlotMerger
    __mergeslots__ = ["digits", "designators", "separators"]

    digits = {}
    designators = {}
    separators = {}

    def __init__(self, *elements):
        self.elements = list(elements)

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

    def copy(self):
        return type(self)(*self.elements)

    def merge(self, other, destructive=False):
        if isinstance(other, type(self)):
            merged = self if destructive else self.copy()
            for i, elt in enumerate(merged.elements):
                merged.elements[i] = merged.elements[i] if elt \
                                                        else other.elements[i]
            return merged
        else:
            for i, elt in enumerate(self.elements):
                if isinstance(other, type(elt)):
                    merged = self if destructive else self.copy()
                    merged.elements[i] = other
                    return merged

    def __getattr__(self, name):
        for elt in self.elements:
            if any(c.__name__.lower() == name for c in type(elt).__mro__):
                return elt
        for elt in self.elements:
            if isinstance(elt, TimeRep):
                attr = getattr(elt, name, None)
                if attr:
                    return attr
        raise AttributeError("%r representation has no element %r" % \
                                 (type(self).__name__, name))

    def __getitem__(self, key):
        if isinstance(key, int):
            return self.elements[key]

    def __iter__(self):
        for elt in self.elements:
            if isinstance(elt, TimeRep):
                for x in elt:
                    yield x
            else:
                yield elt

    def __eq__(self, other):
        return all(map(eq, self, other))

class TimePoint(TimeRep):
    pass

class Date(TimePoint):
    digits = {"Y": Year, "M": Month, "D": Day, "w": Week}
    designators = {"W": None} # for week date
    separators = {u"-": False, # hyphen-minus (a.k.a. ASCII hyphen, U+002D)
                  u"‐": False} # hyphen (U+2010)

    def merge(self, other, destructive=False):
        if isinstance(other, Time):
            return DateTime(self, other)
        else:
            return super(Date, self).merge(other, destructive)

class CalendarDate(Date):
    digits = {"Y": Year, "M": Month, "D": DayOfMonth}

    @units(Year, Month, Day)
    def __init__(self, *args):
        self.check_accuracy(*args)
        super(CalendarDate, self).__init__(*args)

class OrdinalDate(Date):
    digits = {"Y": Year, "D": DayOfYear}

    @units(Year, Day)
    def __init__(self, *args):
        self.check_accuracy(*args)
        super(OrdinalDate, self).__init__(*args)

class WeekDate(Date):
    digits = {"Y": Year, "w": Week, "D": DayOfWeek}

    @units(Year, Week, Day)
    def __init__(self, *args):
        self.check_accuracy(*args)
        super(WeekDate, self).__init__(*args)

class UTCOffset(TimePoint):
    digits = {"h": Hour, "m": Minute}

    @units(Hour, Minute)
    def __init__(self, hour=0, minute=None):
        self.check_accuracy(hour, minute)
        super(UTCOffset, self).__init__(hour, minute)

UTC = UTCOffset(0)

class Time(TimePoint):
    digits = {"h": Hour, "m": Minute, "s": Second}
    designators = {"T": None, "Z": UTC}
    separators = {":": False}

    @units(Hour, Minute, Second, UTCOffset)
    def __init__(self, hour=None, minute=None, second=None, offset=None):
        self.check_accuracy(hour, minute, second)
        super(Time, self).__init__(hour, minute, second, offset)

    def merge(self, other, destructive=False):
        if isinstance(other, Hour) and other.signed:
            return Time(self.hour, self.minute, self.second, UTCOffset(other))
        else:
            return super(Time, self).merge(other, destructive)

class DateTime(Date, Time):
    designators = {"T": Time}

    @units(Date, Time)
    def __init__(self, date, time):
        self.check_accuracy(date, time)
        TimeRep.__init__(self, date, time)

    def merge(self, other, destructive=False):
        if isinstance(other, (Hour, Minute, Second, UTCOffset)):
            return DateTime(self.date, self.time.merge(other))
        elif isinstance(other, (DateTime, Duration)):
            return TimeInterval(self, other)
        else:
            return super(DateTime, self).merge(other, destructive)

class TimeDuration(TimeRep):
    """Represents a duration consisting of hours, minutes, and seconds.

    This class exists primarily because the [M] designator in a duration
    representation is ambiguous; before a [T] it means months, but after
    it means minutes. In order to disambiguate, [T] switches the syntax
    class to this class."""

    digits = {"n": TimeUnit}
    designators = {"H": Hours, "M": Minutes, "S": Seconds}

    @units(Hours, Minutes, Seconds)
    def __init__(self, hours=0, minutes=0, seconds=0):
        self.check_accuracy(hours, minutes, seconds)
        super(TimeDuration, self).__init__(hours, minutes, seconds)

class Duration(TimeRep):
    digits = {"n": TimeUnit}
    designators = {"W": Weeks, "Y": Years, "M": Months, "D": Days,
                   "T": TimeDuration}

    @units(Years, Months, Days, Hours, Minutes, Seconds)
    def __init__(self, *args):
        self.check_accuracy(*args)
        super(Duration, self).__init__(*args)

    def merge(self, other, destructive=False):
        if isinstance(other, Weeks):
            return WeeksDuration(other) # weeks don't mix with other elements
        elif isinstance(other, TimeDuration):
            return Duration(self.years, self.months, self.days,
                            other.hours, other.minutes, other.seconds)
        elif isinstance(other, DateTime):
            return TimeInterval(self, other)
        else:
            return super(Duration, self).merge(other, destructive)

class WeeksDuration(Duration):
    @units(Weeks)
    def __init__(self, weeks=None):
        super(Duration, self).__init__(weeks)

class TimeInterval(DateTime):
    designators = {"P": Duration}
    separators = {"/": True}

    def __init__(self, *args):
        assert len(args) <= 2, "too many end-points for a time interval"
        TimeRep.__init__(self, *args)

class RecurringTimeInterval(TimeInterval):
    digits = {"n": Recurrences}
    designators = {"R": None} # will be RecurringTimeInterval; see below

    @units(Recurrences)
    def __init__(self, *args):
        assert len(args) <= 3
        TimeRep.__init__(self, *args)

    def merge(self, other, destructive=False):
        if isinstance(other, (DateTime, Duration)):
            return RecurringTimeInterval(*(self.elements + [other]))
        else:
            return super(RecurringTimeInterval, self).merge(other, destructive)

# We can't do this assignment in the class definition above, because the
# class doesn't exist at that time.
RecurringTimeInterval.designators["R"] = RecurringTimeInterval

# We allow the user to specify the format representations used for the
# interchange of dates and times. Usually, these will be one of the format
# representations defined in ISO 8601; e.g., [YYYYMMDD] for a calendar date
# or [YYYY-MM-DDThh:mm:ss] for calendar date and local time. Some deviation
# from the standard format representations is permitted, but only to a point.
# Format representations can be used for both reading and formatting (printing)
# of date and time representations.

# Format representations are parsed by the FormatReprParser class into a list
# of operations for a simple virtual machine implemented by the Format class.
# These operations are called format ops, or fops.

class StopFormat(Exception):
    """Halt the execution of a format machine."""
    pass

class FormatOp(object):
    def format(self, m):
        """Format the next element in the input and push the result onto the
        stack. Returns False if the element can not be formatted."""
        return False

    def read(self, m):
        """Read zero or more characters from the input, and possibly push a
        new element onto the stack. Returns True if the top elements of the
        stack should be merged, and False otherwise."""
        raise StopFormat

class Literal(FormatOp):
    """Produce or consume a literal string."""

    def __init__(self, lit):
        self.lit = lit.upper() # see section 3.4.1, note 1

    def format(self, m):
        m.stack.append(self.lit)
        return True

    def read(self, m):
        if not self.lit or m.input.startswith(self.lit, m.i):
            m.i += len(self.lit)
            return False
        else:
            raise StopFormat("expected [%s], got [%s]" % \
                                 (self.lit, m.input[m.i:m.i+len(self.lit)]))

    def __eq__(self, other):
        return ((isinstance(other, basestring) and self.lit == other.upper()) or
                (isinstance(other, type(self)) and self.lit == other.lit))

    def __repr__(self):
        return "%s(%r)" % (type(self).__name__, self.lit)

class Separator(Literal):
    def __init__(self, lit, hard=False):
        super(Separator, self).__init__(lit)
        self.hard = hard

    def format(self, m):
        # We push the literal onto a separate stack so that we don't output
        # a separator before elements that have been elided due to accuracy
        # reduction. The next fop will pick it up if it needs to.
        m.separators.append(self.lit)
        return True

    def read(self, m):
        super(Separator, self).read(m)
        if self.hard:
            # By pushing the identity unit onto the stack, we can ensure that
            # the previous element will not be merged with the next one.
            m.stack.append(unit)
            return True
        else:
            return False

class Designator(Literal):
    """A designator indicates a change in syntax in the format representation;
     e.g., from date to time."""

    def __init__(self, lit, cls):
        super(Designator, self).__init__(lit)
        self.cls = cls

    def format(self, m):
        m.stack.append(m.separators.pop() if m.separators else "")
        return super(Designator, self).format(m)

    def read(self, m):
        super(Designator, self).read(m)
        if self.cls:
            m.stack.append(self.cls())
        return True

    def __eq__(self, other):
        return super(Designator, self).__eq__(other) and self.cls is other.cls

class Coerce(Designator):
    """A postfix designator, like the ones used in duration representations."""

    def read(self, m):
        """Coerce the element on the top of the stack to a different type."""
        Literal.read(self, m)
        m.stack[-1] = self.cls(m.stack[-1])
        return True

class UTCDesignator(Designator):
    """A special-purpose designator representing UTC."""

    def __init__(self):
        super(UTCDesignator, self).__init__("Z", UTCOffset)

    def read(self, m):
        super(Designator, self).read(m)
        m.stack.append(UTC)
        return True

Z = UTCDesignator()

class Element(FormatOp):
    """A fixed-width representation of a unit of time, possibly with sign
    and decimal fraction components."""

    def __init__(self, cls, digits, frac=(0,0), separator=",", signed=False):
        assert issubclass(cls, TimeUnit)
        self.cls = cls
        self.min, self.max = digits
        self.frac_min, self.frac_max = frac
        self.separator = separator
        self.signed = signed
        self.pattern = re.compile(("(%s[0-9]{%d,%s})" % \
                                       ("[+-]" if signed else "",
                                        self.min, self.max or "")) +
                                  (("[.,]([0-9]{%d,%s})" % \
                                        (self.frac_min, self.frac_max or "")) \
                                       if self.frac_min else ""))

    def format(self, m):
        elt = m.input.next()
        if elt and issubclass(type(elt), self.cls):
            s = m.separators.pop() if m.separators else ""
            if self.signed:
                s += "-" if elt.value < 0 else "+"
            whole = abs(int(elt.value))
            frac = abs(elt.value) - whole
            s += ("%0*d" % (self.min, whole))[0:self.max]
            if self.frac_min > 0:
                s += self.separator
                if frac and isinstance(frac, Decimal):
                    q = (Decimal(10) ** -self.frac_max) if self.frac_max \
                                                        else frac
                    exp = frac.quantize(q).as_tuple()[2]
                    frac *= Decimal(10) ** (-exp if -exp > self.frac_min \
                                                 else self.frac_min)
                    s += "".join(str(int(frac)))
                else:
                    # The scaling we do above won't work for 0; just fake it.
                    s += "0"*self.frac_min
            m.stack.append(s)
            return True

    def read(self, m):
        match = self.pattern.match(m.input[m.i:])
        if match:
            digits = match.group(1)
            frac = match.group(2) if self.frac_min else None
            m.stack.append(self.cls(Decimal(".".join((digits, frac))) \
                                        if frac else int(digits),
                                    signed=self.signed))
            m.i += len(digits)
            if frac:
                m.i += len(digits) + 1 # +1 for decimal separator
            return not self.signed # don't merge signed elements
        else:
            raise StopFormat("expected digit; got [%s]" % m.input[m.i])

    def __eq__(self, other):
        return (isinstance(other, type(self)) and
                self.cls is other.cls and
                self.min == other.min and
                self.max == other.max and
                self.frac_min == other.frac_min and
                self.frac_max == other.frac_max and
                self.signed == other.signed)

    def __repr__(self):
        return "%s(%s, (%s, %s), (%s, %s), %r, %r)" \
            % (type(self).__name__,
               self.cls.__name__,
               self.min, self.max,
               self.frac_min, self.frac_max,
               self.separator, self.signed)

class FormatReprParser(object):
    def __init__(self, syntax, format_repr):
        self.initial_syntax = syntax
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
            if designate is UTC:
                # Special case: UTC designator.
                return Z
            elif designate and issubclass(designate, TimeUnit):
                # Postfix designator: coerce the last element.
                return Coerce(char, designate)
            else:
                if designate:
                    self.stack.append(designate) # push new syntax class
                return Designator(char, designate)

    def separator(self, char):
        for level, cls in enumerate(reversed(self.stack)):
            if char in cls.separators:
                for i in range(level):
                    self.stack.pop()
                return Separator(char, cls.separators[char])

    def element(self, char):
        """Consume as many of the same digit-representing characters as
        possible from the format representation and return an Element fop."""
        signed = False
        if char == u"±":
            signed = True
            char = self.next()

        def snarf():
            n = 0
            repeat = False
            while self.peek() == char:
                n += 1
                self.next()
            if self.peek() == u"\u0332": # combining low line (underline)
                repeat = True
                n -= 1 # last char was underlined; don't count it
                self.next() # discard underline
            return n, repeat
        n, repeat = snarf()
        n += 1 # for the char that sparked this call
        if self.peek() in (",", "."):
            separator = self.next()
            frac, frac_repeat = snarf()
        else:
            separator = None
            frac, frac_repeat = 0, False
        return Element(self.syntax.digits[char],
                       (n, None if repeat else n),
                       (frac, None if frac_repeat else frac),
                       separator, signed)

    @property
    def syntax(self):
        return self.stack[-1]

    def parse(self):
        self.stack = [self.initial_syntax]
        for char in self:
            yield (self.designator(char) or
                   self.separator(char) or
                   self.element(char))

class Format(object):
    def __init__(self, format_repr, syntax=RecurringTimeInterval):
        self.ops = list(FormatReprParser(syntax, format_repr).parse())

    def format(self, timerep):
        self.separators = []
        self.stack = []
        if isinstance(timerep, TimeRep):
            self.input = iter(timerep)
        elif isinstance(timerep, TimeUnit):
            self.input = iter([timerep])
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

    def read(self, string):
        self.input = string.upper()
        self.i = 0
        self.stack = []
        ops = iter(self.ops)
        n = len(self.input)
        while self.i < n:
            if ops.next().read(self) and len(self.stack) > 1:
                merged = self.stack[-2].merge(self.stack[-1])
                if merged:
                    self.stack[-2:] = [merged]

        # Now we merge bottom-up. These merges must all succeed.
        obj = self.stack[0]
        for i in range(1, len(self.stack)):
            merged = obj.merge(self.stack[i])
            if not merged:
                raise StopFormat("can't merge elements %r, %r" \
                                     % (obj, self.stack[i]))
            obj = merged
        return obj
