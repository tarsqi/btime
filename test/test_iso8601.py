# -*- mode: Python; coding: utf-8 -*-

from unittest import *

from iso8601 import *

class TestParseRepr(TestCase):
    class X(TimePoint):
        """Dummy time element."""
        digits = {"X": TimeUnit}
        separators = ["-"]

    def assertFormatRepr(self, format_repr, op):
        self.assertEqual(parse_format_repr(self.X, format_repr).next(), op)

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

def suite():
    return TestSuite([TestLoader().loadTestsFromTestCase(cls) \
                          for cls in (TestParseRepr,)])

def run(runner=TextTestRunner, **args):
    return runner(**args).run(suite())

if __name__ == "__main__":
    run(verbosity=2)
