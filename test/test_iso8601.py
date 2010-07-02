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
    def assertFormat(self, format_repr, representation, obj):
        format = Format(format_repr)
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

def suite():
    return TestSuite([TestLoader().loadTestsFromTestCase(cls) \
                          for cls in (TestFormatReprParser,
                                      TestCalendarDate,
                                      TestOrdinalDate,
                                      TestWeekDate,)])

def run(runner=TextTestRunner, **args):
    return runner(**args).run(suite())

if __name__ == "__main__":
    run(verbosity=2)
