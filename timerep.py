"""Representations of dates and times as specified by ISO 8601:2004(E).

Unlike most date & time libraries, this one is designed to allow arbitrarily
ordered piecemeal construction of dates and times."""

import re

__all__ = ["InvalidTimeElement", "InvalidDateTime",
           "CalendarDate", "OrdinalDate", "WeekDate",
           "Time", "UTCOffset", "UTC", "DateTime",
           "Year", "Month", "Week", "DayOfYear", "DayOfMonth", "DayOfWeek",
           "Hour", "Minute", "Second"]

class InvalidTimeElement(Exception):
    def __init__(self, element, value):
        self.element = element
        self.value = value

    def __str__(self):
        return "invalid %s: %s" % (self.element.__class__.__name__.lower(),
                                   self.value)

class InvalidDateTime(Exception):
    pass

class BaseDateTime(object):
    prefix = ""
    separator = ""

    def __init__(self, *elements):
        """Given a list of elements in most-significant-first order,
        check for legitimate omissions."""
        # Omission of elements is allowed only if all of the more
        # significant elements are supplied.
        lse = -1
        for i, elt in reversed(tuple(enumerate(elements))):
            if lse >= 0 and not elt:
                raise InvalidDateTime("invalid date/time accuracy reduction")
            elif elt and lse < 0:
                lse = i
        self.elements = elements[0:lse+1 if lse is not None else None]
        self.reduced_accuracy = lse < len(elements) - 1

    def __len__(self):
        return len(self.elements)

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__,
                           ", ".join(map(repr, self.elements)))

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            # This doesn't deal with reduced accuracy representations.
            return self.elements == other.elements
        else:
            return NotImplemented

    def __lt__(self, other):
        if isinstance(other, self.__class__):
            return self.elements < other.elements # lexicographic ordering
        else:
            return NotImplemented

    def iso8601(self, extended=False):
        separator = self.separator or (self.extsep if extended else "")
        return (self.prefix +
                separator.join((elt.iso8601(extended)
                                for elt in self.elements)))

    __str__ = iso8601

class Date(BaseDateTime):
    extsep = "-"

class CalendarDate(Date):
    """A calendar date, as specified by section 4.1.2."""

    def __init__(self, year, month=None, day=None):
        year, month, day = (ensure_element(year, Year),
                            ensure_element(month, Month),
                            ensure_element(day, DayOfMonth))
        super(CalendarDate, self).__init__(year, month, day)

    def iso8601(self, extended=False):
        if len(self) == 2:
            # Special case, as mandated by section 4.1.2.3: if only the day
            # is omitted, a separator is always used.
            extended = True
        return super(CalendarDate, self).iso8601(extended)

class OrdinalDate(Date):
    """An ordinal date, as specified by section 4.1.3."""

    def __init__(self, year, day=None):
        year, day = (ensure_element(year, Year),
                     ensure_element(day, DayOfYear))
        super(OrdinalDate, self).__init__(year, day)

class WeekDate(Date):
    """A week date, as specified by section 4.1.4."""

    def __init__(self, year, week=None, day=None):
        year, week, day = (ensure_element(year, Year),
                           ensure_element(week, Week),
                           ensure_element(day, DayOfWeek))
        super(WeekDate, self).__init__(year, week, day)

class Time(BaseDateTime):
    """Time of day, as specified by section 4.2."""

    extsep = ":"

    def __init__(self, hour, minute=None, second=None, offset=None):
        hour, minute, second = (ensure_element(hour, Hour),
                                ensure_element(minute, Minute),
                                ensure_element(second, Second))
        assert offset is None or isinstance(offset, UTCOffset), "invalid offset"
        super(Time, self).__init__(hour, minute, second)
        self.offset = offset

    def iso8601(self, extended=False):
        return super(Time, self).iso8601(extended) + \
            (self.offset.iso8601(extended) if self.offset else "")

class UTCOffset(BaseDateTime):
    """Difference between local time and UTC of day (section 4.2.5.1)."""

    extsep = ":"

    def __init__(self, hour=0, minute=None):
        hour, minute = (ensure_element(hour, Hour),
                        ensure_element(minute, Minute))
        super(UTCOffset, self).__init__(hour, minute)

    def iso8601(self, extended=False):
        if any(map(lambda x: x != 0, self.elements)):
            return ("-" if self < UTC else "+") + \
                super(UTCOffset, self).iso8601(extended)
        else:
            return "Z"

class DateTime(BaseDateTime):
    """A date and time of day expression, as specified by section 4.3."""

    separator = "T"

    def __init__(self, date, time):
        assert date is None or isinstance(date, Date)
        assert time is None or isinstance(time, Time)
        if time and date and date.reduced_accuracy:
            raise InvalidDateTime("can't have time with an incomplete date")
        super(DateTime, self).__init__(date, time)

class PartialTime(object):
    """Represents some portion of a possibly incomplete date and time.
    The elements need not be ordered in any way. Attributes are computed
    lazily based on the class names of the elements."""

    def __init__(self, elements=[]):
        self.elements = frozenset(elements)

    def __getattr__(self, name):
        for elt in self.elements:
            if elt.__class__.__name__.lower() == name:
                setattr(self, name, elt) # cache for future lookups
                return elt
        return None # N.B.: don't throw an AttributeError

    def __add__(self, other):
        return PartialTime(self.elements | frozenset([other]))

    def __eq__(self, other):
        return (isinstance(other, self.__class__) and
                self.elements == other.elements)

    def iso8601(self, extended=False):
        return DateTime(CalendarDate(self.year, self.month, self.dayofmonth),
                        Time(self.hour, self.minute, self.second)).iso8601(extended)

    __str__ = iso8601

class TimeElement(PartialTime):
    def __init__(self, value, pattern=re.compile(r"([0-9]+)")):
        if isinstance(value, basestring):
            m = pattern.match(value)
            if not m:
                raise InvalidTimeElement(self, value)
            self.value = int(m.group(1))
        elif isinstance(value, int):
            self.value = value
        else:
            raise InvalidTimeElement(self, value)
        if not self.isvalid():
            raise InvalidTimeElement(self, value)

        super(TimeElement, self).__init__([self])

    def isvalid(self):
        return self.value > 0

    def iso8601(self, extended=False):
        return "%02d" % self.value

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

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, self.value)

def ensure_element(obj, cls):
    return obj if obj is None or isinstance(obj, cls) else cls(obj)

class Year(TimeElement):
    def isvalid(self):
        return 0 <= self.value < 10000

    def iso8601(self, extended=False):
        if self.value < 100:
            return "%02d" % self.value # century
        else:
            return "%04d" % self.value # year

class Month(TimeElement):
    def isvalid(self):
        return 1 <= self.value <= 12

class Week(TimeElement):
    def isvalid(self):
        return 1 <= self.value <= 53

    def iso8601(self, extended=False):
        return "W%02d" % self.value

class DayOfYear(TimeElement):
    def isvalid(self):
        return 1 <= self.value <= 366

    def iso8601(self, extended=False):
        return "%03d" % self.value

class DayOfMonth(TimeElement):
    def isvalid(self):
        return 1 <= self.value <= 31

class DayOfWeek(TimeElement):
    def isvalid(self):
        return 1 <= self.value <= 7

    def iso8601(self, extended=False):
        return "%d" % self.value

class Hour(TimeElement):
    """An hour. We allow negative hours to express differences from UTC."""

    def __neg__(self):
        return self.__class__(-self.value)

    def isvalid(self):
        return 0 <= abs(self.value) <= 24

    def iso8601(self, extended=False):
        return "%02d" % abs(self.value)

class Minute(TimeElement):
    def isvalid(self):
        return 0 <= self.value < 60

class Second(TimeElement):
    def isvalid(self):
        return 0 <= self.value <= 60 # don't forget leap seconds!

# A constant Coordinated Universal Time value. It's important to do this
# assignment here, at the end of the module, so that all of the necessary
# classes are correctly defined.
UTC = UTCOffset(0)
