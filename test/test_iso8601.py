# -*- mode: Python; coding: utf-8 -*-

from unittest import *

from iso8601 import *

class TestFormatReprParser(TestCase):
    class X(TimePoint):
        """Dummy time element."""
        digits = {"X": TimeUnit}
        designators = {"T": Time}
        separators = ["-"]

    def assertFormatRepr(self, format_repr, op):
        parser = FormatReprParser(self.X, format_repr)
        self.assertEqual(parser.parse().next(), op)

    def test_element(self):
        """Time elements with min/max digits in format representation"""
        self.assertFormatRepr(u"X̲", Element(TimeUnit, 0))
        self.assertFormatRepr(u"_X", Element(TimeUnit, 0))
        self.assertFormatRepr(u"X", Element(TimeUnit, 1, 1))
        self.assertFormatRepr(u"XX̲", Element(TimeUnit, 1))
        self.assertFormatRepr(u"X_X", Element(TimeUnit, 1))
        self.assertFormatRepr(u"XXX̲", Element(TimeUnit, 2))
        self.assertFormatRepr(u"XX_X", Element(TimeUnit, 2))
        self.assertFormatRepr(u"XX", Element(TimeUnit, 2, 2))

    def test_signed_element(self):
        """Signed time element in format representation"""
        self.assertFormatRepr(u"±XXXX", Element(TimeUnit, 4, 4, True))

    def test_separator(self):
        """Separator in format representation"""
        self.assertFormatRepr("-", Separator("-"))

    def test_designator(self):
        """Designator in format representation"""
        self.assertFormatRepr("T", Designator("T", Time))

class RepresentationTestCase(TestCase):
    def assertFormat(self, format_repr, representation, obj, syntax=None):
        format = Format(format_repr, syntax) if syntax else Format(format_repr)
        self.assertEqual(format.read(representation), obj)
        self.assertEqual(format.format(obj), representation)

class TestCalendarDate(RepresentationTestCase):
    """Section 4.1.2."""

    def test_complete(self):
        """4.1.2.2"""
        date = CalendarDate(1985, 4, 12)
        self.assertFormat("YYYYMMDD", "19850412", date) # basic format
        self.assertFormat("YYYY-MM-DD", "1985-04-12", date) # extended format

    def test_reduced(self):
        """4.1.2.3"""
        self.assertFormat("YYYY-MM", "1985-04", CalendarDate(1985, 4))
        self.assertFormat("YYYY", "1985", Year(1985))
        self.assertFormat("YY", "19", Year(19)) # not actually a century

    def test_expanded(self):
        """4.1.2.4"""
        # a) A specific day
        date = CalendarDate(1985, 4, 12)
        self.assertFormat(u"±YYYYYYMMDD", "+0019850412", date) # basic format
        self.assertFormat(u"±YYYYYY-MM-DD", "+001985-04-12", date) # extended

        # b) A specific month
        month = CalendarDate(1985, 4)
        self.assertFormat(u"±YYYYYYMM", "+00198504", month) # basic format
        self.assertFormat(u"±YYYYYY-MM", "+001985-04", month) # extended format

        # c) A specific year
        self.assertFormat(u"±YYYYYY", "+001985", Year(1985))

        # d) A specific century
        self.assertFormat(u"±YYYY", "+0019", Year(19)) # not actually a century

class TestOrdinalDate(RepresentationTestCase):
    """Section 4.1.3."""

    def test_complete(self):
        """4.1.3.2"""
        date = OrdinalDate(1985, 102)
        self.assertFormat("YYYYDDD", "1985102", date) # basic format
        self.assertFormat("YYYY-DDD", "1985-102", date) # extended format

    def test_expanded(self):
        """4.1.3.3"""
        date = OrdinalDate(1985, 102)
        self.assertFormat(u"±YYYYYYDDD", "+001985102", date) # basic format
        self.assertFormat(u"±YYYYYY-DDD", "+001985-102", date) # extended format

class TestWeekDate(RepresentationTestCase):
    """Section 4.1.4."""

    def test_complete(self):
        """4.1.4.2"""
        date = WeekDate(1985, 15, 5)
        self.assertFormat("YYYYWwwD", "1985W155", date) # basic format
        self.assertFormat("YYYY-Www-D", "1985-W15-5", date) # extended format

    def test_reduced(self):
        """4.1.4.3"""
        # A specific week
        week = WeekDate(1985, 15)
        self.assertFormat("YYYYWww", "1985W15", week) # basic format
        self.assertFormat("YYYY-Www", "1985-W15", week) # extended format

    def test_expanded(self):
        """4.1.4.4"""
        # a) A specific day
        date = CalendarDate(1985, 4, 12)
        self.assertFormat(u"±YYYYYYMMDD", "+0019850412", date) # basic format
        self.assertFormat(u"±YYYYYY-MM-DD", "+001985-04-12", date) # extended

        # b) A specific month
        month = CalendarDate(1985, 4)
        self.assertFormat(u"±YYYYYYMM", "+00198504", month) # basic format
        self.assertFormat(u"±YYYYYY-MM", "+001985-04", month) # extended format

        # c) A specific year
        self.assertFormat(u"±YYYYYY", "+001985", Year(1985))

        # d) A specific century
        self.assertFormat(u"±YYYY", "+0019", Year(19)) # not actually a century

class TestLocalTime(RepresentationTestCase):
    """Section 4.2.2."""

    def test_complete(self):
        """4.2.2.2"""
        time = Time(23, 20, 50)
        self.assertFormat("hhmmss", "232050", time, Time) # basic format
        self.assertFormat("hh:mm:ss", "23:20:50", time, Time) # basic format

    def test_reduced(self):
        """4.2.2.3"""
        # a) A specific hour and minute
        time = Time(23, 20)
        self.assertFormat("hhmm", "2320", time, Time) # basic format
        self.assertFormat("hh:mm", "23:20", time, Time) # basic format

        # b) A specific hour
        self.assertFormat("hh", "23", Hour(23), Time)

    def test_decimal_fraction(self):
        """4.2.2.4"""
        # a) A specific hour, minute, and second and a decimal fraction of
        # the second
        time = Time(23, 20, 50.5)
        self.assertFormat(u"hhmmss,ss̲", "232050,5", time, Time) # basic format
        self.assertFormat(u"hh:mm:ss,ss̲", "23:20:50,5", time, Time) # extended

        # b) A specific hour and minute and a decimal fraction of the minute
        time = Time(23, 20.8)
        self.assertFormat(u"hhmm,mm̲", "2320,8", time, Time) # basic format
        self.assertFormat(u"hh:mm,mm̲", "23:20,8", time, Time) # extended format

        # c) A specific hour and a decimal fraction of the hour
        self.assertFormat(u"hh,hh̲", "23,3", Time(23.3), Time)

    def test_with_designator(self):
        """4.2.2.5"""
        time = Time(23, 20, 50)
        self.assertFormat("Thhmmss", "T232050", time)

class TestUTC(RepresentationTestCase):
    def test(self):
        """4.2.4"""
        # Basic format
        self.assertFormat("hhmmssZ", "232030Z", Time(23, 20, 30, offset=UTC), Time)
        self.assertFormat("hhmmZ", "2320Z", Time(23, 20, offset=UTC), Time)
        self.assertFormat("hhZ", "23Z", Time(23, offset=UTC), Time)

        # Extended format
        self.assertFormat("hh:mm:ssZ", "23:20:30Z", Time(23, 20, 30, offset=UTC), Time)
        self.assertFormat("hh:mmZ", "23:20Z", Time(23, 20, offset=UTC), Time)

class TestLocalTimeAndUTC(RepresentationTestCase):
    def test_difference(self):
        """4.2.5.1"""
        # Basic format
        self.assertFormat(u"±hhmm", "+0100", UTCOffset(1, 0))
        self.assertFormat(u"±hh", "+01", Hour(1, signed=True))

        # Extended format
        self.assertFormat(u"±hh:mm", "+01:00", UTCOffset(1, 0))

    def test_local_time_and_difference(self):
        """4.2.5.2"""
        # Basic format
        self.assertFormat(u"hhmmss±hhmm", "152746+0100",
                          Time(15, 27, 46, UTCOffset(1, 0)))
        self.assertFormat(u"hhmmss±hhmm", "152746-0500",
                          Time(15, 27, 46, UTCOffset(-5, 0)))
        self.assertFormat(u"hhmmss±hh", "152746+01",
                          Time(15, 27, 46, UTCOffset(1)))
        self.assertFormat(u"hhmmss±hh", "152746-05",
                          Time(15, 27, 46, UTCOffset(-5)))

        # Extended format
        self.assertFormat(u"hh:mm:ss±hh:mm", "15:27:46+01:00",
                          Time(15, 27, 46, UTCOffset(1, 0)))
        self.assertFormat(u"hh:mm:ss±hh:mm", "15:27:46-05:00",
                          Time(15, 27, 46, UTCOffset(-5, 0)))
        self.assertFormat(u"hh:mm:ss±hh", "15:27:46+01",
                          Time(15, 27, 46, UTCOffset(1)))
        self.assertFormat(u"hh:mm:ss±hh", "15:27:46-05",
                          Time(15, 27, 46, UTCOffset(-5)))

def suite():
    return TestSuite([TestLoader().loadTestsFromTestCase(cls) \
                          for cls in (TestFormatReprParser,
                                      TestCalendarDate,
                                      TestOrdinalDate,
                                      TestWeekDate,
                                      TestLocalTime,
                                      TestUTC,
                                      TestLocalTimeAndUTC,)])

def run(runner=TextTestRunner, **args):
    return runner(**args).run(suite())

if __name__ == "__main__":
    run(verbosity=2)
