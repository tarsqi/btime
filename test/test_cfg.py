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
        self.assertTrue(RegexpTerminal("foo+").match("fooooo"))

    def test_mismatch(self):
        """Fail to match a regular expression"""
        self.assertFalse(Literal("foo+").match("fo"))
        self.assertFalse(Literal("foo+").match(None))

class TestAcronym(TestCase):
    def test_match_without(self):
        """Match an acronym without periods"""
        self.assertTrue(Acronym("ad").match("ad"))

    def test_match_with(self):
        """Match an acronym with periods"""
        self.assertTrue(Acronym("ad").match("a.d."))

    def test_specified_with_match_without(self):
        """Match an acronym without periods, but specified with periods"""
        self.assertTrue(Acronym("a.d.").match("ad"))

    def test_specified_with_match_with(self):
        """Match an acronym with periods that was specified with periods"""
        self.assertTrue(Acronym("a.d.").match("a.d."))

    def test_mismatch(self):
        """Fail to match an acronym"""
        self.assertFalse(Acronym("ad").match("add"))

    def test_invalid(self):
        """Reject an invalid acronym"""
        self.assertRaises(ValueError, lambda: Acronym("ad$"))

class TestAbbrev(TestCase):
    def setUp(self):
        self.abbrev = Abbrev("foobar", 3)

    def test_match(self):
        """Match a whole or abbreviation"""
        self.assertTrue(self.abbrev.match("foobar"))
        self.assertTrue(self.abbrev.match("foo"))
        self.assertTrue(self.abbrev.match("foob"))
        self.assertTrue(self.abbrev.match("foo."))
        self.assertTrue(self.abbrev.match("foob."))

    def test_mismatch(self):
        """Fail to match an abbreviation"""
        self.assertFalse(self.abbrev.match("bar"))
        self.assertFalse(self.abbrev.match("foo.bar"))
        self.assertFalse(self.abbrev.match("fooq"))
        self.assertFalse(self.abbrev.match("foobarbaz"))

def suite():
    return TestSuite([TestLoader().loadTestsFromTestCase(cls) \
                          for cls in (TestLiteral,
                                      TestRegexp,
                                      TestAcronym,
                                      TestAbbrev)])

def run(runner=TextTestRunner, **args):
    return runner(**args).run(suite())

if __name__ == "__main__":
    run(verbosity=2)
