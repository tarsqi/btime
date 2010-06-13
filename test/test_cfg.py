from unittest import *

from cfg import *

class TestLiteral(TestCase):
    def test_match(self):
        """Match a literal string"""
        self.assertTrue(Literal("foo").match("foo"))

    def test_mismatch(self):
        """Fail to match a literal string"""
        self.assertFalse(Literal("foo").match("bar"))

class TestRegexp(TestCase):
    def test_match(self):
        """Match a regular expression"""
        self.assertTrue(Regexp("foo+").match("fooooo"))

    def test_mismatch(self):
        """Fail to match a regular expression"""
        self.assertFalse(Literal("foo+").match("fo"))

class TestAbbrev(TestCase):
    def setUp(self):
        self.abbrev = Abbrev("foobar", 3)

    def test_match(self):
        """Match a whole or abbreviation"""
        self.assertTrue(self.abbrev.match("foobar"))
        self.assertTrue(self.abbrev.match("foo"))
        self.assertTrue(self.abbrev.match("foo."))

    def test_mismatch(self):
        """Fail to match an abbreviation"""
        self.assertFalse(self.abbrev.match("bar"))
        self.assertFalse(self.abbrev.match("foo.bar"))

def suite():
    return TestSuite([TestLoader().loadTestsFromTestCase(cls) \
                          for cls in (TestLiteral,
                                      TestRegexp,
                                      TestAbbrev)])

def run(runner=TextTestRunner, **args):
    return runner(**args).run(suite())

if __name__ == "__main__":
    run(verbosity=2)
