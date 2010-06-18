# -*- mode: Python; coding: utf-8 -*-

from unittest import *

from timerep import *
from timerep import BaseDateTime, TimeElement, ensure_element

class TestBaseDateTime(TestCase):
    def test_invalid_accuracy_reduction(self):
        """Ensure invalid accuracy reduction is detected"""
        self.assertRaises(InvalidDateTime,
                          lambda: BaseDateTime(True, False, True))

    def test_accuracy_reduction(self):
        """Allow valid accuracy reduction"""
        bdt = BaseDateTime(True, True, False)
        self.assertTrue(bdt)
        self.assertTrue(bdt.reduced_accuracy)
        self.assertEqual(len(bdt), 2)

    def test_full_accuracy(self):
        """Accept full-accuracy representation"""
        bdt = BaseDateTime(True, True, True)
        self.assertTrue(bdt)
        self.assertFalse(bdt.reduced_accuracy)
        self.assertEqual(len(bdt), 3)

    def test_comparison(self):
        """Comparisons of date/time representations"""
        self.assertTrue(BaseDateTime(3, 2, 1) < BaseDateTime(4))
        self.assertTrue(BaseDateTime(3, 2, 1) < BaseDateTime(3, 2, 2))
        self.assertEqual(BaseDateTime(3, 2, 1), BaseDateTime(3, 2, 1))
        self.assertEqual(BaseDateTime(3, 2, 0), BaseDateTime(3, 2))

class TestTimeElement(TestCase):
    def test_init_from_int(self):
        """Time element from integer"""
        elt = TimeElement(42)
        self.assertEqual(elt, 42)

    def test_init_from_string(self):
        """Time element from string"""
        elt = TimeElement("42")
        self.assertEqual(elt, 42)

    def test_invalid(self):
        """Invalid time element"""
        self.assertRaises(InvalidTimeElement, lambda: TimeElement("foo"))

    def test_equality(self):
        """Equality of time elements"""
        self.assertEqual(TimeElement(42), TimeElement("42"))
        self.assertEqual(TimeElement(42), 42)

    def test_inequality(self):
        """Inequality of time elements"""
        self.assertNotEqual(TimeElement(42), TimeElement(24))
        self.assertNotEqual(TimeElement(42), 24)

    def test_lt(self):
        """Comparison of time elements"""
        self.assertTrue(TimeElement(1) < TimeElement(2))
        self.assertTrue(TimeElement(1) < 2)

    def test_subtraction(self):
        u"""(Naïve) subtraction of time elements"""
        self.assertEqual(TimeElement(3) - TimeElement(2), TimeElement(1))
        self.assertEqual(TimeElement(3) - 2, TimeElement(1))

class TestEnsureElement(TestCase):
    def test_none(self):
        """Ensure None is a valid element"""
        self.assertTrue(ensure_element(None, Hour) is None)

    def test_instance(self):
        """Ensure an element instance is an element"""
        elt = Hour(5)
        self.assertTrue(ensure_element(elt, Hour) is elt)

    def test_coerce(self):
        """Coerce an integer to a time element"""
        self.assertEqual(ensure_element(5, Hour), Hour(5))

class TestYear(TestCase):
    def test_valid(self):
        """Valid year"""
        year = Year(2000)
        self.assertEqual(year, 2000)
        self.assertEqual(year.iso8601(), "2000")

    def test_invalid(self):
        """Invalid year"""
        self.assertRaises(InvalidTimeElement, lambda: Year(-500))

class TestMonth(TestCase):
    def test_valid(self):
        """Valid month"""
        month = Month(3)
        self.assertEqual(month, 3)
        self.assertEqual(month.iso8601(), "03")

    def test_invalid(self):
        """Invalid month"""
        self.assertRaises(InvalidTimeElement, lambda: Month(13))

class TestWeek(TestCase):
    def test_valid(self):
        """Valid calendar week"""
        week = Week(15)
        self.assertEqual(week, 15)
        self.assertEqual(week.iso8601(), "W15")

    def test_invalid(self):
        """Invalid calendar week"""
        self.assertRaises(InvalidTimeElement, lambda: Week(54))

class TestDayOfYear(TestCase):
    def test_valid(self):
        """Valid day of year"""
        day = DayOfYear(155)
        self.assertEqual(day, 155)
        self.assertEqual(day.iso8601(), "155")

    def test_invalid(self):
        """Invalid day of year"""
        self.assertRaises(InvalidTimeElement, lambda: DayOfYear(367))

class TestDayOfMonth(TestCase):
    def test_valid(self):
        """Valid day of month"""
        day = DayOfMonth(15)
        self.assertEqual(day, 15)
        self.assertEqual(day.iso8601(), "15")

    def test_invalid(self):
        """Invalid day of month"""
        self.assertRaises(InvalidTimeElement, lambda: DayOfMonth(32))

class TestDayOfWeek(TestCase):
    def test_valid(self):
        """Valid day of week"""
        day = DayOfWeek(5)
        self.assertEqual(day, 5)
        self.assertEqual(day.iso8601(), "5")

    def test_invalid(self):
        """Invalid day of week"""
        self.assertRaises(InvalidTimeElement, lambda: DayOfWeek(8))

class TestDaysNotEqual(TestCase):
    def test_days(self):
        """Not all days are created equal"""
        self.assertNotEqual(DayOfMonth(4), DayOfWeek(4))
        self.assertNotEqual(DayOfWeek(4), DayOfYear(4))
        self.assertNotEqual(DayOfMonth(4), DayOfYear(4))

class TestCalendarDate(TestCase):
    def test_elements(self):
        """Calendar date elements"""
        date = CalendarDate(1985, 4, 12)
        self.assertEqual(date.year, Year(1985))
        self.assertEqual(date.month, Month(4))
        self.assertEqual(date.day, DayOfMonth(12))

    def test_complete_representation(self):
        """Complete representation of a calendar date"""
        # section 4.1.2.2
        date = CalendarDate(1985, 4, 12)
        self.assertFalse(date.reduced_accuracy)
        self.assertEqual(date.iso8601(False), "19850412")
        self.assertEqual(date.iso8601(True), "1985-04-12")

    def test_specific_month(self):
        """A specific month"""
        # section 4.1.2.3 (a)
        date = CalendarDate(1985, 4)
        self.assertTrue(date.reduced_accuracy)
        self.assertEqual(date.iso8601(), "1985-04")

    def test_specific_year(self):
        """A specific year"""
        # section 4.1.2.3 (b)
        date = CalendarDate(1985)
        self.assertTrue(date.reduced_accuracy)
        self.assertEqual(date.iso8601(), "1985")

    def test_specific_century(self):
        """A specific century"""
        # section 4.1.2.3 (c)
        date = CalendarDate(19)
        self.assertTrue(date.reduced_accuracy)
        self.assertEqual(date.iso8601(), "19")

class TestOrdinalDate(TestCase):
    def test_elements(self):
        """Ordinal date elements"""
        date = OrdinalDate(1985, 102)
        self.assertEqual(date.year, Year(1985))
        self.assertEqual(date.day, DayOfYear(102))

    def test_complete_representation(self):
        """Complete representation of an ordinal date"""
        # section 4.1.3.2
        date = OrdinalDate(1985, 102)
        self.assertFalse(date.reduced_accuracy)
        self.assertEqual(date.iso8601(False), "1985102")
        self.assertEqual(date.iso8601(True), "1985-102")

class TestWeekDate(TestCase):
    def test_elements(self):
        """Week date elements"""
        date = WeekDate(1985, 15, 5)
        self.assertEqual(date.year, Year(1985))
        self.assertEqual(date.week, Week(15))
        self.assertEqual(date.day, DayOfWeek(5))

    def test_complete_representation(self):
        """Complete representation of a week date"""
        # section 4.1.4.2
        date = WeekDate(1985, 15, 5)
        self.assertFalse(date.reduced_accuracy)
        self.assertEqual(date.iso8601(False), "1985W155")
        self.assertEqual(date.iso8601(True), "1985-W15-5")

    def test_specific_week(self):
        """A specific week"""
        # section 4.1.4.3
        date = WeekDate(1985, 15)
        self.assertTrue(date.reduced_accuracy)
        self.assertEqual(date.iso8601(False), "1985W15")
        self.assertEqual(date.iso8601(True), "1985-W15")

class TestTime(TestCase):
    def test_complete_representation(self):
        """Complete representation of local time"""
        # section 4.2.2.2
        time = Time(23, 20, 50)
        self.assertFalse(time.reduced_accuracy)
        self.assertEqual(time.iso8601(False), "232050")
        self.assertEqual(time.iso8601(True), "23:20:50")

    def test_specific_hour_minute(self):
        """A specific hour and minute"""
        # section 4.2.2.3 (a)
        time = Time(23, 20)
        self.assertTrue(time.reduced_accuracy)
        self.assertEqual(time.iso8601(False), "2320")
        self.assertEqual(time.iso8601(True), "23:20")

    def test_specific_hour(self):
        """A specific hour"""
        # section 4.2.2.3 (b)
        time = Time(23)
        self.assertTrue(time.reduced_accuracy)
        self.assertEqual(time.iso8601(), "23")

    def test_utc_of_day(self):
        """UTC of day"""
        # section 4.2.4
        hh, mm, ss = Hour(23), Minute(20), Second(30)
        # basic format
        self.assertEqual(Time(hh, mm, ss, UTC).iso8601(False), "232030Z")
        self.assertEqual(Time(hh, mm, offset=UTC).iso8601(False), "2320Z")
        self.assertEqual(Time(hh, offset=UTC).iso8601(False), "23Z")
        # extended format
        self.assertEqual(Time(hh, mm, ss, UTC).iso8601(True), "23:20:30Z")
        self.assertEqual(Time(hh, mm, offset=UTC).iso8601(True), "23:20Z")

    def test_local_time_and_difference(self):
        """Local time and difference from UTC"""
        # section 4.2.5.2
        hh, mm, ss = Hour(15), Minute(27), Second(46)
        geneva_hhmm = UTCOffset(1, 0)
        geneva_hh = UTCOffset(1)
        new_york_hhmm = UTCOffset(-5, 0)
        new_york_hh = UTCOffset(-5)
        self.assertEqual(Time(hh, mm, ss, geneva_hhmm).iso8601(False),
                         "152746+0100")
        self.assertEqual(Time(hh, mm, ss, new_york_hhmm).iso8601(False),
                         "152746-0500")
        self.assertEqual(Time(hh, mm, ss, geneva_hh).iso8601(False),
                         "152746+01")
        self.assertEqual(Time(hh, mm, ss, new_york_hh).iso8601(False),
                         "152746-05")

class TestUTCOffset(TestCase):
    def test_utc(self):
        """Test the UTC object"""
        self.assertEqual(UTC.iso8601(), "Z")

    def test_offset(self):
        """Difference between local time and UTC of day"""
        # section 4.2.5.1
        self.assertEqual(UTCOffset(1, 0).iso8601(False), "+0100")
        self.assertEqual(UTCOffset(1).iso8601(False), "+01")
        self.assertEqual(UTCOffset(1, 0).iso8601(True), "+01:00")

class TestDateTime(TestCase):
    def test_complete_representation(self):
        """Complete representation of date and time"""
        # section 4.3.2
        datetime = DateTime(CalendarDate(1985, 4, 12), Time(10, 15, 30))
        self.assertEqual(datetime.iso8601(False), "19850412T101530")
        self.assertEqual(datetime.iso8601(True), "1985-04-12T10:15:30")

    def test_calendar_date_time(self):
        """Calendar date and time"""
        # section 4.3.3 (a)
        datetime = DateTime(CalendarDate(1985, 4, 12), Time(10, 15))
        self.assertEqual(datetime.iso8601(False), "19850412T1015")
        self.assertEqual(datetime.iso8601(True), "1985-04-12T10:15")

    def test_ordinal_date_time(self):
        """Ordinal date and UTC of day"""
        # section 4.3.3 (b)
        datetime = DateTime(OrdinalDate(1985, 102), Time(10, 15, None, UTC))
        self.assertEqual(datetime.iso8601(False), "1985102T1015Z")
        self.assertEqual(datetime.iso8601(True), "1985-102T10:15Z")

    def test_week_date_local_time(self):
        """Week date and local time and the difference from UTC"""
        # section 4.3.3 (c)
        datetime = DateTime(WeekDate(1985, 15, 5),
                            Time(10, 15, None, UTCOffset(4, 0)))
        self.assertEqual(datetime.iso8601(False), "1985W155T1015+0400")
        self.assertEqual(datetime.iso8601(True), "1985-W15-5T10:15+04:00")

    def test_invalid_reduction(self):
        """Invalid accuracy reduction in date and time representation"""
        self.assertRaises(InvalidDateTime,
                          lambda: DateTime(CalendarDate(1985), Time(10, 15)))

class TestPartialTime(TestCase):
    def test_partial_date(self):
        """Construct a partial date from a year and a month"""
        date = Year(2000) + Month(3)
        self.assertEqual(date.year, 2000)
        self.assertEqual(date.month, 3)
        self.assertEqual(date.day, None)
        self.assertEqual(date.iso8601(), "2000-03")

    def test_commutativity(self):
        """Ensure that addition of partial times is commutative"""
        self.assertEqual(DayOfMonth(12) + Year(2000) + Month(3),
                         Month(3) + Year(2000) + DayOfMonth(12))

    def test_partial_datetime(self):
        """Construct a partial date and time"""
        datetime = Year(2000) + Month(3) + DayOfMonth(12) + Hour(14) + Minute(6)
        self.assertEqual(datetime.iso8601(True), "2000-03-12T14:06")

def suite():
    return TestSuite([TestLoader().loadTestsFromTestCase(cls) \
                          for cls in (TestBaseDateTime,
                                      TestTimeElement,
                                      TestEnsureElement,
                                      TestYear,
                                      TestMonth,
                                      TestWeek,
                                      TestDayOfYear,
                                      TestDayOfMonth,
                                      TestDayOfWeek,
                                      TestCalendarDate,
                                      TestOrdinalDate,
                                      TestWeekDate,
                                      TestTime,
                                      TestUTCOffset,
                                      TestDateTime,
                                      TestPartialTime)])

def run(runner=TextTestRunner, **args):
    return runner(**args).run(suite())

if __name__ == "__main__":
    run(verbosity=2)
